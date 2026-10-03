from decimal import Decimal
import datetime
from django.db import transaction
from django.utils import timezone
from apps.customers.models import Customer
from apps.products.models import Product
from apps.routes.models import Driver
from .models import Order, OrderItem, OrderActivityLog

def generate_order_number():
    """Generates unique sequential order number for today."""
    today_str = timezone.localdate().strftime("%Y%m%d")
    count = Order.objects.filter(order_number__startswith=f"ORD-{today_str}").count() + 1
    order_num = f"ORD-{today_str}-{count:04d}"
    while Order.objects.filter(order_number=order_num).exists():
        count += 1
        order_num = f"ORD-{today_str}-{count:04d}"
    return order_num


def create_order_service(customer_id, items_data, order_date=None, driver_id=None, notes="", created_by=None, shop_expense=None, shop_expense_notes="", source="MANAGER", entered_by_role="", entered_by_name="", entered_by_type="MANAGER", order_number=None):
    """
    Atomic business transaction to create an order with line items.
    """
    if not items_data:
        raise ValueError("At least one order item is required.")

    if order_date is None:
        order_date = timezone.localdate()

    with transaction.atomic():
        customer = Customer.objects.select_for_update().get(id=customer_id)
        route = customer.route

        driver = None
        if driver_id:
            driver = Driver.objects.get(id=driver_id)
        elif route:
            driver = route.drivers.filter(is_active=True).first()

        if not order_number or not str(order_number).strip():
            order_number = generate_order_number()
        else:
            order_number = str(order_number).strip()
            if Order.objects.filter(order_number=order_number).exists():
                order_number = f"{order_number}-{generate_order_number().split('-')[-1]}"

        # Determine initial status based on source
        initial_status = Order.Status.LOCKED if source in ["MANAGER", "OWNER"] else Order.Status.SUBMITTED
        now_ts = timezone.now()

        # Aggregate items by product_id to prevent duplicate OrderItem rows
        aggregated_items = {}
        for item in items_data:
            pid = str(item["product_id"])
            qty = int(item["quantity"])
            u_price = item.get("unit_price")
            if pid in aggregated_items:
                aggregated_items[pid]["quantity"] += qty
                if u_price is not None:
                    aggregated_items[pid]["unit_price"] = u_price
            else:
                aggregated_items[pid] = {
                    "product_id": pid,
                    "quantity": qty,
                    "unit_price": u_price
                }

        # Resolve unit prices for items
        for pid, item in aggregated_items.items():
            product = Product.objects.get(id=pid)
            from apps.customers.services import get_effective_product_price
            effective_price, has_custom, _ = get_effective_product_price(customer, product)
            if "unit_price" in item and item["unit_price"] is not None and str(item["unit_price"]).strip() != "":
                sent_price = Decimal(str(item["unit_price"]))
                if has_custom and sent_price == product.unit_price:
                    u_price = effective_price
                else:
                    u_price = sent_price
            else:
                u_price = effective_price
            item["resolved_unit_price"] = u_price
            item["product_obj"] = product

        # Double-Submit / Idempotency Protection: If identical order (same items, qty, and price) was submitted in last 5s, return existing
        recent_cutoff = now_ts - datetime.timedelta(seconds=5)
        recent_duplicate = Order.objects.filter(
            customer=customer,
            order_date=order_date,
            source=source,
            created_at__gte=recent_cutoff,
        ).prefetch_related("items").first()
        if recent_duplicate:
            existing_items_set = {
                (str(it.product_id), it.quantity, it.unit_price)
                for it in recent_duplicate.items.all()
            }
            new_items_set = {
                (pid, item["quantity"], item["resolved_unit_price"])
                for pid, item in aggregated_items.items()
            }
            if existing_items_set == new_items_set:
                return recent_duplicate

        # Create base order
        order = Order.objects.create(
            order_number=order_number,
            customer=customer,
            route=route,
            driver=driver,
            order_date=order_date,
            submitted_at=now_ts if initial_status in [Order.Status.SUBMITTED, Order.Status.LOCKED, Order.Status.CONFIRMED] else None,
            status=initial_status,
            total_amount=Decimal("0.00"),
            shop_expense=Decimal("0.00"),
            shop_expense_notes=shop_expense_notes or "",
            notes=notes,
            created_by=created_by,
            source=source,
            entered_by_role=entered_by_role,
            entered_by_user=created_by,
            entered_by_name=entered_by_name or (created_by.get_full_name() if created_by else "")
        )

        total_amount = Decimal("0.00")

        # Create order items from aggregated items
        for pid, item in aggregated_items.items():
            product = item["product_obj"]
            quantity = item["quantity"]
            unit_price = item["resolved_unit_price"]
            subtotal = (Decimal(quantity) * unit_price).quantize(Decimal("0.01"))

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                entered_by_type=entered_by_type,
                entered_by_user=created_by,
            )

            total_amount += subtotal

        exp_dec = Decimal(str(shop_expense or "0.00")).quantize(Decimal("0.01"))
        order.shop_expense = exp_dec
        order.shop_expense_notes = shop_expense_notes or ""
        order.total_amount = max(Decimal("0.00"), total_amount - exp_dec).quantize(Decimal("0.01"))
        order.save(update_fields=["total_amount", "shop_expense", "shop_expense_notes", "updated_at"])

        # Create immutable activity log
        log_action = "Order Created (Manager/Owner)" if source in ["MANAGER", "OWNER"] else "Order Created via Customer Link"
        OrderActivityLog.objects.create(
            order=order,
            action=log_action,
            user_name=order.entered_by_name,
            user_role=order.entered_by_role,
            source=source,
            details={
                "items_count": len(aggregated_items),
                "total_amount": str(order.total_amount)
            }
        )

        # Synchronize delivery dispatch when assigned to a driver or route driver
        from apps.deliveries.services import ensure_order_delivery
        ensure_order_delivery(order, driver=driver, route=route)

    return order


def update_order_service(order_id, items_data=None, driver_id=None, route_id=None, notes=None, user=None, shop_expense=None, shop_expense_notes=None):
    """
    Safely edits an order. 
    Orders that are SUBMITTED or LOCKED cannot be edited unless reopened.
    """
    with transaction.atomic():
        order = Order.objects.select_for_update().select_related("customer", "route", "driver").get(id=order_id)

        from apps.deliveries.models import Delivery

        if order.status in [Order.Status.DELIVERED, Order.Status.COMPLETED, Order.Status.CANCELLED]:
            raise ValueError(f"Cannot edit order #{order.order_number} because its status is already {order.get_status_display()}.")

        if hasattr(order, "delivery") and order.delivery and order.delivery.status == Delivery.Status.DELIVERED:
            raise ValueError(f"Cannot edit order #{order.order_number} because the delivery is already Delivered.")

        old_total = order.total_amount
        old_driver = order.driver.user.get_full_name() if (order.driver and order.driver.user) else "Unassigned"

        if route_id is not None:
            from apps.routes.models import Route
            route = Route.objects.get(id=route_id)
            order.route = route
            order.save(update_fields=["route", "updated_at"])

        if driver_id is not None:
            if driver_id:
                driver = Driver.objects.get(id=driver_id)
                order.driver = driver
                order.save(update_fields=["driver", "updated_at"])
            else:
                order.driver = None
                order.save(update_fields=["driver", "updated_at"])
                if hasattr(order, "delivery") and order.delivery:
                    order.delivery.driver = None
                    order.delivery.save(update_fields=["driver", "updated_at"])

        from apps.deliveries.services import ensure_order_delivery
        if order.driver or (order.route and order.route.drivers.filter(is_active=True).exists()):
            ensure_order_delivery(order, driver=order.driver, route=order.route)

        if notes is not None:
            order.notes = notes

        if shop_expense is not None:
            order.shop_expense = Decimal(str(shop_expense)).quantize(Decimal("0.01"))
        if shop_expense_notes is not None:
            order.shop_expense_notes = shop_expense_notes

        if items_data is not None:
            if not items_data:
                raise ValueError("An order must have at least one line item.")

            # Aggregate items by product_id to prevent duplicates
            aggregated_items = {}
            for item in items_data:
                pid = str(item["product_id"])
                qty = int(item["quantity"])
                u_price = item.get("unit_price")
                if pid in aggregated_items:
                    aggregated_items[pid]["quantity"] += qty
                    if u_price is not None:
                        aggregated_items[pid]["unit_price"] = u_price
                else:
                    aggregated_items[pid] = {
                        "product_id": pid,
                        "quantity": qty,
                        "unit_price": u_price
                    }

            order.items.all().delete()
            total_amount = Decimal("0.00")
            for pid, item in aggregated_items.items():
                product = Product.objects.get(id=pid)
                quantity = item["quantity"]
                from apps.customers.services import get_effective_product_price
                effective_price, has_custom, _ = get_effective_product_price(order.customer, product)
                if "unit_price" in item and item["unit_price"] is not None and str(item["unit_price"]).strip() != "":
                    sent_price = Decimal(str(item["unit_price"]))
                    if has_custom and sent_price == product.unit_price:
                        unit_price = effective_price
                    else:
                        unit_price = sent_price
                else:
                    unit_price = effective_price

                subtotal = (Decimal(quantity) * unit_price).quantize(Decimal("0.01"))
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    subtotal=subtotal,
                    entered_by_type="MANAGER",
                    entered_by_user=user,
                )
                total_amount += subtotal

            order.total_amount = max(Decimal("0.00"), total_amount - order.shop_expense).quantize(Decimal("0.01"))
        elif shop_expense is not None:
            items_sum = sum(item.subtotal for item in order.items.all())
            order.total_amount = max(Decimal("0.00"), items_sum - order.shop_expense).quantize(Decimal("0.01"))

        # Re-lock if edited by manager/owner
        order.status = Order.Status.LOCKED
        order.save()

        # Audit log
        user_name = user.get_full_name() or user.username if user else "System"
        user_role = user.role if user else "SYSTEM"
        OrderActivityLog.objects.create(
            order=order,
            action="Order Edited & Locked",
            user_name=user_name,
            user_role=user_role,
            source="MANAGER",
            details={
                "old_total": str(old_total),
                "new_total": str(order.total_amount),
            }
        )

        from apps.common.audit import log_activity
        log_activity(
            user=user,
            action="UPDATED",
            entity_type="ORDER",
            entity_id=order.id,
            entity_name=f"Order #{order.order_number}",
            summary=f"Updated order #{order.order_number} total to ₹{order.total_amount}",
            details={
                "old_total": str(old_total),
                "new_total": str(order.total_amount),
            },
        )

    return order

def reopen_order_service(order_id, user, reason):
    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)
        if hasattr(order, "delivery") and order.delivery and order.delivery.status == "DELIVERED":
             raise ValueError("Cannot reopen order because delivery has already been marked as Delivered.")
             
        old_status = order.status
        order.status = Order.Status.DRAFT
        order.save(update_fields=["status", "updated_at"])
        
        user_name = user.get_full_name() or user.username
        OrderActivityLog.objects.create(
            order=order,
            action="Order Reopened",
            user_name=user_name,
            user_role=user.role,
            source="MANAGER",
            details={
                "reason": reason,
                "previous_status": old_status
            }
        )
        return order

