from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.common.models import TimeStampedUUIDModel
from apps.customers.models import Customer
from apps.orders.models import Order

class Payment(TimeStampedUUIDModel):
    """
    Financial payment record collected from a customer shop.
    Supports Cash and GPay/UPI, with complete audit trail.
    """
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        GPAY_UPI = "GPAY_UPI", "GPay / UPI"

    class Status(models.TextChoices):
        COMPLETED = "COMPLETED", "Completed"
        REVERSED = "REVERSED", "Reversed"
        VOID = "VOID", "Void"

    payment_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text="Unique receipt identifier (e.g. PAY-20260926-0001)"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="payments",
        help_text="Customer making the payment"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        help_text="Associated order if collected specifically for an order"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Payment amount in INR (always Decimal)"
    )
    payment_method = models.CharField(
        max_length=20,
        choices=Method.choices,
        default=Method.CASH,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.COMPLETED,
        db_index=True
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="UPI Reference ID / Transaction Ref / Receipt Ref"
    )
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="collected_payments",
        help_text="Staff member (driver/manager) who received the funds"
    )
    received_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Exact timestamp payment was received"
    )
    notes = models.TextField(blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversed_payments",
        help_text="Staff member who reversed or voided this payment"
    )
    reversed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of reversal/void"
    )
    reversal_reason = models.TextField(
        blank=True,
        help_text="Mandatory audit explanation for reversal"
    )

    class Meta:
        ordering = ["-received_at", "-created_at"]
        verbose_name = "Payment Record"
        verbose_name_plural = "Payment Records"

    def __str__(self):
        return f"{self.payment_number} - {self.customer.name} (₹{self.amount} via {self.payment_method})"
