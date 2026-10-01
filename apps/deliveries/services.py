import datetime
from django.db import transaction
from django.utils import timezone
from apps.orders.models import Order
from apps.routes.models import Driver
from .models import Delivery

def generate_delivery_number(for_date=None):
    """
    Generates a unique, collision-proof sequential delivery dispatch number.
    e.g. DEL-20261001-0001
    """
    if for_date is None:
        target_date = timezone.localdate()
    elif isinstance(for_date, str):
        target_date = datetime.date.fromisoformat(for_date)
    elif hasattr(for_date, "date"):
        target_date = for_date.date()
    else:
        target_date = for_date

    today_str = target_date.strftime("%Y%m%d")
    count = Delivery.objects.filter(delivery_number__startswith=f"DEL-{today_str}").count() + 1
    deliv_num = f"DEL-{today_str}-{count:04d}"
    while Delivery.objects.filter(delivery_number=deliv_num).exists():
        count += 1
        deliv_num = f"DEL-{today_str}-{count:04d}"
    return deliv_num


def ensure_order_delivery(order, driver=None, route=None):
    """
    Ensures that an Order has a corresponding Delivery dispatch record assigned
    to the correct driver and route.
    If the order does not have a driver, attempts to resolve from the route's active driver.
    Collision-safe, idempotent, atomic.
    """
    with transaction.atomic():
        # Resolve route
        target_route = route or order.route
        if not target_route and order.customer and order.customer.route:
            target_route = order.customer.route

        # Resolve driver
        target_driver = driver or order.driver
        if not target_driver and target_route:
            target_driver = target_route.drivers.filter(is_active=True).first()

        order_updates = []
        if target_route and order.route_id != target_route.id:
            order.route = target_route
            order_updates.append("route")
        if target_driver and order.driver_id != target_driver.id:
            order.driver = target_driver
            order_updates.append("driver")
        if order_updates:
            order_updates.append("updated_at")
            order.save(update_fields=order_updates)

        if not target_driver or not target_route:
            return None

        # Check if Delivery already exists for this order
        delivery = getattr(order, "delivery", None)
        if not delivery:
            try:
                delivery = Delivery.objects.select_for_update().get(order=order)
            except Delivery.DoesNotExist:
                delivery = None

        if delivery:
            deliv_updates = []
            if delivery.driver_id != target_driver.id:
                delivery.driver = target_driver
                deliv_updates.append("driver")
            if delivery.route_id != target_route.id:
                delivery.route = target_route
                deliv_updates.append("route")
            if deliv_updates:
                deliv_updates.append("updated_at")
                delivery.save(update_fields=deliv_updates)
            return delivery

        # Create new delivery dispatch
        deliv_num = generate_delivery_number(for_date=order.order_date)
        delivery = Delivery.objects.create(
            order=order,
            delivery_number=deliv_num,
            driver=target_driver,
            route=target_route,
            status=Delivery.Status.ASSIGNED,
        )
        return delivery


def complete_delivery_service(delivery_id, recipient_name="", notes="", user=None):
    """
    Atomically marks delivery and associated order as DELIVERED,
    and updates the customer's credit ledger with a CREDIT_SALE entry.
    """
    with transaction.atomic():
        delivery = Delivery.objects.select_for_update().select_related("order", "order__customer", "driver").get(id=delivery_id)

        if delivery.status == Delivery.Status.DELIVERED:
            return delivery

        delivery.status = Delivery.Status.DELIVERED
        delivery.delivered_at = timezone.now()
        if recipient_name:
            delivery.recipient_name = recipient_name
        if notes:
            delivery.notes = notes
        delivery.save()

        # Update order status
        order = delivery.order
        order.status = Order.Status.DELIVERED
        order.save(update_fields=["status", "updated_at"])

        # Post credit sale to customer's ledger
        from apps.credits.services import record_credit_sale_service
        record_credit_sale_service(order=order, recorded_by=user)

        from apps.common.audit import log_activity
        log_activity(
            user=user,
            action="DELIVERED",
            entity_type="DELIVERY",
            entity_id=delivery.id,
            entity_name=f"Delivery #{delivery.delivery_number}",
            summary=f"Marked delivery #{delivery.delivery_number} for {order.customer.name} as Delivered",
            details={
                "delivery_number": delivery.delivery_number,
                "order_number": order.order_number,
                "customer": order.customer.name,
                "recipient_name": recipient_name,
            },
        )

    return delivery


def mark_delivery_not_delivered_service(delivery_id, failed_reason, notes="", user=None):
    """
    Atomically marks delivery and associated order as NOT_DELIVERED with required reason.
    Does NOT post credit sale to ledger.
    """
    if not failed_reason:
        raise ValueError("A reason is mandatory when marking a delivery as Not Delivered.")

    with transaction.atomic():
        delivery = Delivery.objects.select_for_update().select_related("order", "order__customer", "driver").get(id=delivery_id)
        delivery.status = Delivery.Status.NOT_DELIVERED
        delivery.failed_reason = failed_reason
        if notes:
            delivery.notes = notes
        delivery.save()

        order = delivery.order
        order.status = Order.Status.NOT_DELIVERED
        order.save(update_fields=["status", "updated_at"])

        from apps.common.audit import log_activity
        log_activity(
            user=user,
            action="NOT_DELIVERED",
            entity_type="DELIVERY",
            entity_id=delivery.id,
            entity_name=f"Delivery #{delivery.delivery_number}",
            summary=f"Marked delivery #{delivery.delivery_number} for {order.customer.name} as Not Delivered: {failed_reason}",
            details={
                "delivery_number": delivery.delivery_number,
                "order_number": order.order_number,
                "customer": order.customer.name,
                "failed_reason": failed_reason,
                "notes": notes,
            },
        )

    return delivery


def assign_delivery_driver_service(delivery_id, driver_id, allow_cross_route=False, notes="", user=None):
    """
    Safely assigns or reassigns a delivery to a driver.
    Enforces route compatibility check unless allow_cross_route is True.
    Updates delivery and parent order status.
    """
    from apps.routes.models import Driver

    with transaction.atomic():
        delivery = Delivery.objects.select_for_update().select_related("order", "route", "driver").get(id=delivery_id)

        if delivery.status == Delivery.Status.DELIVERED:
            raise ValueError(f"Cannot reassign Delivery #{delivery.delivery_number} because it has already been delivered.")

        driver = Driver.objects.select_related("assigned_route", "user").get(id=driver_id)
        if not driver.is_active:
            raise ValueError(f"Driver {driver.user.get_full_name() or driver.user.username} is inactive.")

        if driver.assigned_route and delivery.route and driver.assigned_route.id != delivery.route.id and not allow_cross_route:
            raise ValueError(
                f"Driver {driver.user.get_full_name() or driver.user.username} is assigned to route '{driver.assigned_route.name}', "
                f"which does not match delivery route '{delivery.route.name}'. Enable cross-route override to proceed."
            )

        old_driver_name = delivery.driver.user.get_full_name() if (delivery.driver and delivery.driver.user) else "Unassigned"

        delivery.driver = driver
        delivery.status = Delivery.Status.ASSIGNED
        if notes:
            delivery.notes = notes
        delivery.save(update_fields=["driver", "status", "notes", "updated_at"])

        # Sync parent order
        order = delivery.order
        order.driver = driver
        if order.status == Order.Status.PENDING:
            order.status = Order.Status.CONFIRMED
        order.save(update_fields=["driver", "status", "updated_at"])

        from apps.common.audit import log_activity
        log_activity(
            user=user,
            action="ASSIGNED",
            entity_type="DELIVERY",
            entity_id=delivery.id,
            entity_name=f"Delivery #{delivery.delivery_number}",
            summary=f"Assigned Delivery #{delivery.delivery_number} to {driver.user.get_full_name() or driver.user.username}",
            details={
                "delivery_number": delivery.delivery_number,
                "order_number": order.order_number,
                "customer": order.customer.name,
                "old_driver": old_driver_name,
                "new_driver": driver.user.get_full_name() or driver.user.username,
                "allow_cross_route": allow_cross_route,
            },
        )

    return delivery

