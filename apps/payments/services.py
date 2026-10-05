from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.customers.models import Customer
from apps.orders.models import Order
from .models import Payment

def generate_payment_number(payment_date=None):
    """Generates unique sequential payment receipt number for today or given date."""
    if payment_date is None:
        payment_date = timezone.localdate()
    elif isinstance(payment_date, str):
        import datetime
        payment_date = datetime.date.fromisoformat(payment_date)
    date_str = payment_date.strftime("%Y%m%d")
    count = Payment.objects.filter(payment_number__startswith=f"PAY-{date_str}").count() + 1
    pay_num = f"PAY-{date_str}-{count:04d}"
    while Payment.objects.filter(payment_number=pay_num).exists():
        count += 1
        pay_num = f"PAY-{date_str}-{count:04d}"
    return pay_num


def record_payment_service(customer_id, amount, payment_method, collected_by, order_id=None, reference_number="", notes="", received_at=None, staff_member=None, staff_member_id=None):
    """
    Atomic business transaction to record a customer payment.
    - Validates Decimal amount
    - Creates Payment audit record
    - Updates Customer.current_balance
    - Appends entry into Customer Credit Ledger
    """
    amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount <= Decimal("0.00"):
        raise ValueError("Payment amount must be greater than zero.")

    if received_at is None:
        received_at = timezone.now()

    if staff_member_id and not staff_member:
        from apps.accounts.models import StaffMember
        staff_member = StaffMember.objects.filter(id=staff_member_id).first()

    with transaction.atomic():
        customer = Customer.objects.select_for_update().get(id=customer_id)

        order = None
        if order_id:
            order = Order.objects.get(id=order_id)

        pay_date = received_at.date() if hasattr(received_at, "date") else None
        payment_number = generate_payment_number(payment_date=pay_date)

        payment = Payment.objects.create(
            payment_number=payment_number,
            customer=customer,
            order=order,
            amount=amount,
            payment_method=payment_method,
            status=Payment.Status.COMPLETED,
            reference_number=reference_number,
            collected_by=collected_by,
            staff_member=staff_member,
            received_at=received_at,
            notes=notes,
        )

        # Update customer current balance (reduction of receivable)
        new_balance = (customer.current_balance - amount).quantize(Decimal("0.01"))
        customer.current_balance = new_balance
        customer.save(update_fields=["current_balance", "updated_at"])

        # Post to Credit Ledger
        from apps.credits.models import CreditTransaction
        tx_type = (
            CreditTransaction.TransactionType.CASH_PAYMENT
            if payment_method == Payment.Method.CASH
            else CreditTransaction.TransactionType.GPAY_PAYMENT
        )

        allocation_note = f"Order #{order.order_number}" if order else "Previous Credit Balance"
        entry_notes = f"Payment for {allocation_note} via {payment.get_payment_method_display()}."
        if reference_number:
            entry_notes += f" Ref: {reference_number}."
        if notes:
            entry_notes += f" Notes: {notes}."

        CreditTransaction.objects.create(
            customer=customer,
            transaction_type=tx_type,
            amount=-amount,  # negative amount decreases debt/receivable
            balance_after=new_balance,
            reference_payment=payment,
            reference_order=order,
            notes=entry_notes,
            recorded_by=collected_by,
        )

        from apps.common.audit import log_activity
        log_activity(
            user=collected_by,
            action="CREATED",
            entity_type="PAYMENT",
            entity_id=payment.id,
            entity_name=f"Payment #{payment.payment_number}",
            summary=f"Recorded {payment.get_payment_method_display()} payment of ₹{payment.amount} for {customer.name} ({allocation_note})",
            details={
                "payment_number": payment.payment_number,
                "customer": customer.name,
                "amount": str(payment.amount),
                "method": payment.payment_method,
                "allocation": "ORDER_PAYMENT" if order else "PREVIOUS_CREDIT",
                "order_number": order.order_number if order else None,
                "new_balance": str(new_balance),
            },
        )

    return payment


def reverse_payment_service(payment_id, user, reason):
    """
    Atomically reverses / voids an existing payment.
    - Locks Payment and Customer rows.
    - Prohibits reversing an already reversed payment.
    - Requires non-empty audit reason.
    - Restores customer's receivable balance (+amount).
    - Posts PAYMENT_REVERSAL to credit ledger.
    - Logs detailed audit trail.
    """
    if not reason or not reason.strip():
        raise ValueError("A clear reason is required to reverse a payment.")

    clean_reason = reason.strip()

    with transaction.atomic():
        payment = Payment.objects.select_for_update().select_related("customer", "order").get(id=payment_id)

        if payment.status == Payment.Status.REVERSED:
            raise ValueError(f"Payment #{payment.payment_number} has already been reversed.")

        payment.status = Payment.Status.REVERSED
        payment.reversed_by = user
        payment.reversed_at = timezone.now()
        payment.reversal_reason = clean_reason
        payment.save(update_fields=["status", "reversed_by", "reversed_at", "reversal_reason", "updated_at"])

        from apps.credits.services import record_payment_reversal_credit_service
        record_payment_reversal_credit_service(payment=payment, reason=clean_reason, recorded_by=user)

    return payment

