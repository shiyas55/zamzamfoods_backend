from decimal import Decimal
from django.db import transaction
from apps.customers.models import Customer
from .models import CreditTransaction

def record_opening_balance_service(customer, opening_balance, recorded_by=None):
    """
    Sets initial customer opening balance on credit ledger.
    """
    amount = Decimal(str(opening_balance)).quantize(Decimal("0.01"))
    with transaction.atomic():
        customer.current_balance = amount
        customer.save(update_fields=["current_balance", "updated_at"])

        tx = CreditTransaction.objects.create(
            customer=customer,
            transaction_type=CreditTransaction.TransactionType.OPENING_BALANCE,
            amount=amount,
            balance_after=amount,
            notes="Opening receivable balance initialization",
            recorded_by=recorded_by,
        )

        from apps.common.audit import log_activity
        log_activity(
            user=recorded_by,
            action="CREATED",
            entity_type="CREDIT",
            entity_id=tx.id,
            entity_name=f"Opening Balance for {customer.name}",
            summary=f"Initialized opening balance of ₹{amount} for {customer.name}",
            details={"customer": customer.name, "amount": str(amount)},
        )

        return tx


def record_credit_sale_service(order, recorded_by=None):
    """
    Records credit sale for an order.
    Increases customer's current balance (receivable).
    Idempotent: If a CREDIT_SALE ledger entry already exists for this order, returns it without double counting.
    """
    with transaction.atomic():
        existing = CreditTransaction.objects.filter(
            reference_order=order,
            transaction_type=CreditTransaction.TransactionType.CREDIT_SALE
        ).first()
        if existing:
            return existing

        amount = Decimal(str(order.total_amount)).quantize(Decimal("0.01"))
        if amount <= Decimal("0.00"):
            return None

        customer = Customer.objects.select_for_update().get(id=order.customer_id)
        new_balance = (customer.current_balance + amount).quantize(Decimal("0.01"))
        customer.current_balance = new_balance
        customer.save(update_fields=["current_balance", "updated_at"])

        tx = CreditTransaction.objects.create(
            customer=customer,
            transaction_type=CreditTransaction.TransactionType.CREDIT_SALE,
            amount=amount,
            balance_after=new_balance,
            reference_order=order,
            notes=f"Credit sale for order #{order.order_number}",
            recorded_by=recorded_by,
        )

        from apps.common.audit import log_activity
        log_activity(
            user=recorded_by,
            action="CREATED",
            entity_type="CREDIT",
            entity_id=tx.id,
            entity_name=f"Credit Sale for Order #{order.order_number}",
            summary=f"Recorded credit sale ₹{amount} for {customer.name}. New Balance: ₹{new_balance}",
            details={"customer": customer.name, "amount": str(amount), "order_number": order.order_number},
        )

        return tx


def record_adjustment_service(customer_id, amount, notes, recorded_by=None):
    """
    Authorized balance adjustment (positive or negative). Owner/Manager only.
    """
    delta = Decimal(str(amount)).quantize(Decimal("0.01"))
    with transaction.atomic():
        customer = Customer.objects.select_for_update().get(id=customer_id)
        old_balance = customer.current_balance
        new_balance = (customer.current_balance + delta).quantize(Decimal("0.01"))
        customer.current_balance = new_balance
        customer.save(update_fields=["current_balance", "updated_at"])

        tx = CreditTransaction.objects.create(
            customer=customer,
            transaction_type=CreditTransaction.TransactionType.ADJUSTMENT,
            amount=delta,
            balance_after=new_balance,
            notes=notes,
            recorded_by=recorded_by,
        )

        from apps.common.audit import log_activity
        log_activity(
            user=recorded_by,
            action="UPDATED",
            entity_type="CREDIT_ADJUSTMENT",
            entity_id=tx.id,
            entity_name=f"Adjustment for {customer.name}",
            summary=f"Authorized balance adjustment of {'+' if delta >= 0 else ''}₹{delta} for {customer.name}. New Bal: ₹{new_balance}",
            details={
                "customer": customer.name,
                "amount": str(delta),
                "old_balance": str(old_balance),
                "new_balance": str(new_balance),
                "notes": notes,
            },
        )

        return tx


def record_payment_reversal_credit_service(payment, reason, recorded_by=None):
    """
    Records a payment reversal on the credit ledger.
    Restores the customer's receivable balance (+payment.amount).
    """
    amount = Decimal(str(payment.amount)).quantize(Decimal("0.01"))
    with transaction.atomic():
        customer = Customer.objects.select_for_update().get(id=payment.customer_id)
        old_balance = customer.current_balance
        new_balance = (customer.current_balance + amount).quantize(Decimal("0.01"))
        customer.current_balance = new_balance
        customer.save(update_fields=["current_balance", "updated_at"])

        tx = CreditTransaction.objects.create(
            customer=customer,
            transaction_type=CreditTransaction.TransactionType.PAYMENT_REVERSAL,
            amount=amount,
            balance_after=new_balance,
            reference_payment=payment,
            reference_order=payment.order,
            notes=f"Reversal of Payment #{payment.payment_number}: {reason}",
            recorded_by=recorded_by,
        )

        from apps.common.audit import log_activity
        log_activity(
            user=recorded_by,
            action="REVERSED",
            entity_type="PAYMENT_REVERSAL",
            entity_id=tx.id,
            entity_name=f"Reversal of Payment #{payment.payment_number}",
            summary=f"Reversed payment #{payment.payment_number} (₹{amount}) for {customer.name}: {reason}. Balance restored to ₹{new_balance}",
            details={
                "payment_number": payment.payment_number,
                "customer": customer.name,
                "amount": str(amount),
                "old_balance": str(old_balance),
                "new_balance": str(new_balance),
                "reason": reason,
            },
        )

        return tx
