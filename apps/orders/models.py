from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.common.models import TimeStampedUUIDModel
from apps.customers.models import Customer
from apps.routes.models import Route, Driver
from apps.products.models import Product

class Order(TimeStampedUUIDModel):
    """
    Sales order for bakery products placed for a customer shop.
    """
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending"
        CONFIRMATION_PENDING = "CONFIRMATION_PENDING", "Confirmation Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        SUBMITTED = "SUBMITTED", "Submitted"
        LOCKED = "LOCKED", "Locked"
        BILLING = "BILLING", "Billing"
        DELIVERY_CREATED = "DELIVERY_CREATED", "Delivery Created"
        DELIVERED = "DELIVERED", "Delivered"
        NOT_DELIVERED = "NOT_DELIVERED", "Not Delivered"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    order_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text="Human-readable unique order identifier (e.g. ORD-20260926-0001)"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="orders",
        help_text="Customer shop receiving the order"
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name="orders",
        help_text="Delivery route"
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text="Driver assigned to deliver this order"
    )
    order_date = models.DateField(default=timezone.now, db_index=True)
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp when order was submitted"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Calculated total order amount in INR"
    )
    shop_expense = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Shop expense, damages, or returns deducted from order total"
    )
    shop_expense_notes = models.CharField(
        max_length=255,
        blank=True,
        help_text="Remarks/reason for shop expense"
    )
    notes = models.TextField(blank=True)
    
    # Audit & Identity Tracking
    source = models.CharField(
        max_length=50,
        default="MANAGER",
        help_text="Source of the order: CUSTOMER_LINK, MANAGER, OWNER"
    )
    entered_by_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Role of the person who entered the order"
    )
    entered_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_orders"
    )
    entered_by_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name of the person who entered the order (e.g., Customer Name)"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_orders"
    )

    class Meta:
        ordering = ["-order_date", "-created_at"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"{self.order_number} - {self.customer.name} (₹{self.total_amount})"


class OrderItem(TimeStampedUUIDModel):
    """
    Individual item line belonging to an order.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items"
    )
    quantity = models.PositiveIntegerField(help_text="Quantity ordered")
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Unit selling price at time of order"
    )
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Line total (quantity * unit_price)"
    )

    @property
    def total_price(self):
        """Compatibility property for line total."""
        return self.subtotal
    
    # Item-level Identity Tracking
    entered_by_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="CUSTOMER, MANAGER, OWNER"
    )
    entered_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_order_items"
    )

    class Meta:
        ordering = ["product__name"]
        unique_together = [["order", "product"]]
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.product.name} x {self.quantity} = ₹{self.subtotal}"


class OrderActivityLog(TimeStampedUUIDModel):
    """
    Immutable audit log for order lifecycle events.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="activity_logs"
    )
    action = models.CharField(max_length=255)
    user_name = models.CharField(max_length=100, blank=True)
    user_role = models.CharField(max_length=50, blank=True)
    source = models.CharField(max_length=50, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Order Activity Log"
        verbose_name_plural = "Order Activity Logs"

    def __str__(self):
        return f"{self.action} on {self.order.order_number}"
