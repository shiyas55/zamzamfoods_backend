from decimal import Decimal
import datetime
from django.db import transaction
from django.utils import timezone
from apps.customers.models import Customer
from apps.products.models import Product
from apps.routes.models import Driver
from .models import Order, OrderItem, OrderActivityLog

def get_business_date_kolkata(order_date=None):
    """
    Returns datetime.date representing the business date strictly in Asia/Kolkata timezone.
    """
    if order_date is None:
        try:
            import zoneinfo
            kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
            return timezone.now().astimezone(kolkata_tz).date()
        except Exception:
            return timezone.localdate()
    elif isinstance(order_date, str):
        return datetime.date.fromisoformat(str(order_date).strip()[:10])
    elif isinstance(order_date, datetime.datetime):
        try:
            import zoneinfo
            kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
            return order_date.astimezone(kolkata_tz).date()
        except Exception:
            return order_date.date()
    return order_date


def generate_order_number(order_date=None):
    """Generates unique sequential order number strictly tied to the order's business date."""
    order_date = get_business_date_kolkata(order_date)
    date_str = order_date.strftime("%Y%m%d")
    count = Order.objects.filter(order_number__startswith=f"ORD-{date_str}").count() + 1
    order_num = f"ORD-{date_str}-{count:04d}"
    while Order.objects.filter(order_number=order_num).exists():
        count += 1
        order_num = f"ORD-{date_str}-{count:04d}"
    return order_num


_UNSET = object()


def create_order_service(customer_id, items_data, order_date=None, driver_id=_UNSET, notes="", created_by=None, shop_expense=None, shop_expense_notes="", source="MANAGER", entered_by_role="", entered_by_name="", entered_by_type="MANAGER", order_number=None):
    """
    Atomic business transaction to create an order with line items.
    """
    if not items_data:
        raise ValueError("At least one order item is required.")

    order_date = get_business_date_kolkata(order_date)
    date_str = order_date.strftime("%Y%m%d")

    with transaction.atomic():
        customer = Customer.objects.select_for_update().get(id=customer_id)
        route = customer.route

        driver = None
        if driver_id is not _UNSET and driver_id is not None:
            driver = Driver.objects.get(id=driver_id)
        elif driver_id is _UNSET and route:
            driver = route.drivers.filter(is_active=True).first()

        clean_order_num = str(order_number).strip() if order_number else ""
        if not clean_order_num:
            order_number = generate_order_number(order_date=order_date)
        else:
            # Canonical normalization:
            # 1. Plain sequence digits e.g. "22" or "0022" -> "ORD-YYYYMMDD-0022"
            if clean_order_num.isdigit():
                seq_val = int(clean_order_num)
                order_number = f"ORD-{date_str}-{seq_val:04d}"
            # 2. Existing "ORD-" prefix: ensure date segment matches the order's business date
            elif clean_order_num.startswith("ORD-"):
                parts = clean_order_num.split("-")
                if len(parts) >= 3 and parts[1] != date_str:
                    order_number = f"ORD-{date_str}-{parts[2]}"
                else:
                    order_number = clean_order_num
            else:
                order_number = clean_order_num

            if Order.objects.filter(order_number=order_number).exists():
                order_number = f"{order_number}-{generate_order_number(order_date=order_date).split('-')[-1]}"

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
        if driver:
            from apps.deliveries.services import ensure_order_delivery
            ensure_order_delivery(order, driver=driver, route=route)

        # Post credit sale to customer's ledger immediately if order total > 0 and not CANCELLED
        if order.total_amount > Decimal("0.00") and order.status != Order.Status.CANCELLED:
            from apps.credits.services import record_credit_sale_service
            record_credit_sale_service(order=order, recorded_by=created_by)

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

        # Synchronize customer credit balance with order total change.
        # IMPORTANT: We update the existing CREDIT_SALE ledger entry in-place
        # rather than creating a new ADJUSTMENT transaction.
        # Creating an ADJUSTMENT would distort get_customers_opening_balances_for_date()
        # for the order's date and all prior dates, because that formula subtracts
        # all ADJUSTMENT transactions with created_at >= target_date.
        # Updating the CREDIT_SALE in-place keeps one clean ledger entry per order.
        delta = (order.total_amount - old_total).quantize(Decimal("0.01"))
        if delta != Decimal("0.00") and order.status != Order.Status.CANCELLED:
            from apps.credits.models import CreditTransaction
            from apps.credits.services import record_credit_sale_service
            sale_tx = CreditTransaction.objects.filter(
                reference_order=order,
                transaction_type=CreditTransaction.TransactionType.CREDIT_SALE
            ).first()
            if sale_tx:
                customer = Customer.objects.select_for_update().get(id=order.customer_id)
                new_balance = (customer.current_balance + delta).quantize(Decimal("0.01"))
                customer.current_balance = new_balance
                customer.save(update_fields=["current_balance", "updated_at"])
                # Update the CREDIT_SALE entry in-place: amount = new total, adjust balance_after
                new_sale_amount = (sale_tx.amount + delta).quantize(Decimal("0.01"))
                new_sale_balance_after = (sale_tx.balance_after + delta).quantize(Decimal("0.01"))
                sale_tx.amount = new_sale_amount
                sale_tx.balance_after = new_sale_balance_after
                sale_tx.notes = (
                    f"Credit sale for order #{order.order_number} "
                    f"(last edited: ₹{old_total} → ₹{order.total_amount})"
                )
                sale_tx.save(update_fields=["amount", "balance_after", "notes"])
            else:
                record_credit_sale_service(order=order, recorded_by=user)

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

