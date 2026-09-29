from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedUUIDModel

class DailyClosing(TimeStampedUUIDModel):
    """
    Financial snapshot representing a verified daily closing performed by a Manager or Owner.
    Records operational figures, cash & UPI collections, and credit metrics at closing time.
    Reopening is strictly restricted to Owner.
    """
    date = models.DateField(
        unique=True,
        db_index=True,
        help_text="The calendar date being closed"
    )
    # Day Opening
    is_opened = models.BooleanField(
        default=False,
        help_text="True if day was formally opened"
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opened_days",
        help_text="Manager or Owner who opened the day"
    )
    opened_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when day was opened"
    )
    opening_cash = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Opening cash float in register at start of day"
    )
    opening_notes = models.TextField(
        blank=True,
        help_text="Notes recorded during day opening"
    )

    # Day Closing
    is_closed = models.BooleanField(
        default=True,
        help_text="True if closed, False if reopened or in progress"
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_days",
        help_text="Manager or Owner who submitted the daily closing"
    )
    closed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when closing was confirmed"
    )
    reopened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reopened_days",
        help_text="Owner who reopened the closed day"
    )
    reopened_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when day was reopened"
    )
    reopen_reason = models.TextField(
        blank=True,
        help_text="Owner's mandatory explanation for reopening"
    )

    # Financial snapshots
    total_orders = models.IntegerField(default=0)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_collected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cash_collected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    upi_collected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    credit_generated = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    previous_credit_collected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    driver_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    net_collection = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Daily Closing"
        verbose_name_plural = "Daily Closings"

    def __str__(self):
        status_label = "Closed" if self.is_closed else "Reopened"
        return f"Daily Closing ({self.date}): {status_label} - Sales ₹{self.total_sales}, Collected ₹{self.total_collected}"
