from decimal import Decimal
from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedUUIDModel
from apps.customers.models import Customer
from apps.orders.models import Order
from apps.payments.models import Payment

class CreditTransaction(TimeStampedUUIDModel):
    """
    Immutable credit ledger entry for customer debt tracking.
    Preserves complete financial history:
    - Opening balance
    - Credit sales (delivered orders)
    - Cash / GPay payments
    - Authorized balance adjustments
    """
    class TransactionType(models.TextChoices):
        OPENING_BALANCE = "OPENING_BALANCE", "Opening Balance"
        CREDIT_SALE = "CREDIT_SALE", "Credit Sale"
        CASH_PAYMENT = "CASH_PAYMENT", "Cash Payment"
        GPAY_PAYMENT = "GPAY_PAYMENT", "GPay / UPI Payment"
        ORDER_PAYMENT = "ORDER_PAYMENT", "Order Payment"
        PREVIOUS_CREDIT_PAYMENT = "PREVIOUS_CREDIT_PAYMENT", "Previous Credit Payment"
        ADJUSTMENT = "ADJUSTMENT", "Authorized Adjustment"
        PAYMENT_REVERSAL = "PAYMENT_REVERSAL", "Payment Reversal / Void"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="credit_transactions",
        help_text="Customer shop account"
    )
    transaction_type = models.CharField(
        max_length=30,
        choices=TransactionType.choices,
        db_index=True
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Transaction delta in INR (+ increases receivable, - decreases receivable)"
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Snapshot of the customer's balance immediately after this transaction"
    )
    reference_order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_ledger_entries"
    )
    reference_payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="credit_ledger_entries"
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="recorded_credit_transactions",
        help_text="User who triggered or authorized this transaction"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Credit Ledger Entry"
        verbose_name_plural = "Credit Ledger Entries"

    @property
    def balance_before(self):
        """Returns the customer balance prior to this ledger transaction."""
        return (self.balance_after - self.amount).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.customer.name} - {self.transaction_type}: ₹{self.amount} (Bal: ₹{self.balance_after})"
