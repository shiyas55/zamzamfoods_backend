from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.products.models import Product
from .models import Customer, CustomerProductPrice

def get_effective_product_price(customer, product):
    """
    Determines effective selling price for a customer and product:
    1. Checks active CustomerProductPrice for this (customer, product) valid today.
    2. Falls back to product.unit_price if no custom price exists.
    Returns: (price: Decimal, is_custom: bool, price_record_id: Optional[str])
    """
    today = timezone.localdate()
    from django.db.models import Q
    custom_price_obj = CustomerProductPrice.objects.filter(
        customer=customer,
        product=product,
        is_active=True,
        effective_from__lte=today,
    ).filter(
        Q(effective_to__isnull=True) | Q(effective_to__gte=today)
    ).order_by("-effective_from", "-created_at").first()

    if custom_price_obj and custom_price_obj.price > Decimal("0.00"):
        return custom_price_obj.price, True, str(custom_price_obj.id)
    return product.unit_price, False, None


def set_customer_product_price(customer=None, product=None, price=None, effective_from=None, effective_to=None, user=None, customer_id=None, product_id=None):
    """
    Configures or updates customer-specific wholesale price for a product.
    Deactivates any previous active price for this customer+product.
    If price is 0, deactivates custom pricing so it falls back to standard product price.
    """
    if customer is None and customer_id is not None:
        customer = customer_id
    if product is None and product_id is not None:
        product = product_id

    price = Decimal(str(price)).quantize(Decimal("0.01"))
    if price < Decimal("0.00"):
        raise ValueError("Price cannot be negative.")

    if effective_from is None:
        effective_from = timezone.localdate()

    with transaction.atomic():
        cust_obj = customer if isinstance(customer, Customer) else Customer.objects.get(id=customer)
        prod_obj = product if isinstance(product, Product) else Product.objects.get(id=product)

        # Find previous active price for audit log comparison
        prev_price_obj = CustomerProductPrice.objects.filter(
            customer=cust_obj,
            product=prod_obj,
            is_active=True
        ).first()
        old_price_val = str(prev_price_obj.price) if prev_price_obj else str(prod_obj.unit_price)

        # Deactivate existing active prices for this customer & product
        CustomerProductPrice.objects.filter(
            customer=cust_obj,
            product=prod_obj,
            is_active=True
        ).update(is_active=False, updated_by=user)

        if price == Decimal("0.00"):
            # Setting price to 0 clears/resets custom rate back to standard base price
            return None

        # Create new active price
        new_price = CustomerProductPrice.objects.create(
            customer=cust_obj,
            product=prod_obj,
            price=price,
            effective_from=effective_from,
            effective_to=effective_to,
            is_active=True,
            created_by=user,
            updated_by=user,
        )

        from apps.common.audit import log_activity
        log_activity(
            user=user,
            action="UPDATED" if prev_price_obj else "CREATED",
            entity_type="PRICE",
            entity_id=new_price.id,
            entity_name=f"{cust_obj.name} - {prod_obj.name}",
            summary=f"Changed {cust_obj.name}'s {prod_obj.name} price: ₹{old_price_val} → ₹{new_price.price}",
            details={
                "customer": cust_obj.name,
                "product": prod_obj.name,
                "old_price": old_price_val,
                "new_price": str(new_price.price),
            },
        )

    return new_price


def get_customers_opening_balances_for_date(target_date, customer_ids=None):
    """
    Computes opening receivable due for customers at the START of target_date
    (i.e. the balance owed BEFORE that day's orders, payments, and adjustments).

    Formula:
        Opening Balance at start of Date D =
            customer.current_balance
            - Sum(Orders where order_date >= D and status != CANCELLED)
            + Sum(Payments where received_at__date >= D and status = COMPLETED)
            - Sum(Standalone Credit Adjustments where created_at__date >= D
                  and reference_order IS NULL)

    NOTE: ADJUSTMENT transactions that have a reference_order (legacy order-edit
    adjustments created before the in-place CREDIT_SALE update approach) are
    intentionally excluded. The order's CREDIT_SALE entry already reflects the
    current total, so reversing those order-linked adjustments would double-subtract
    the order-edit delta and produce an incorrect Prev. Due.

    Returns: dict { str(customer_id): str(opening_balance_decimal_formatted) }
    """
    import datetime
    from django.db.models import Sum
    from apps.orders.models import Order
    from apps.payments.models import Payment
    from apps.credits.models import CreditTransaction

    if isinstance(target_date, str):
        target_date = datetime.date.fromisoformat(str(target_date).strip()[:10])

    customers_qs = Customer.objects.filter(is_active=True)
    if customer_ids:
        customers_qs = customers_qs.filter(id__in=customer_ids)

    cust_map = {str(c.id): c.current_balance for c in customers_qs}

    orders_agg = (
        Order.objects.filter(order_date__gte=target_date)
        .exclude(status=Order.Status.CANCELLED)
    )
    if customer_ids:
        orders_agg = orders_agg.filter(customer_id__in=customer_ids)
    orders_by_cust = {
        str(row["customer_id"]): (row["total"] or Decimal("0.00"))
        for row in orders_agg.values("customer_id").annotate(total=Sum("total_amount"))
    }

    payments_agg = (
        Payment.objects.filter(received_at__date__gte=target_date, status=Payment.Status.COMPLETED)
    )
    if customer_ids:
        payments_agg = payments_agg.filter(customer_id__in=customer_ids)
    payments_by_cust = {
        str(row["customer_id"]): (row["total"] or Decimal("0.00"))
        for row in payments_agg.values("customer_id").annotate(total=Sum("amount"))
    }

    # Only include legitimate STANDALONE adjustments (reference_order IS NULL).
    # Order-edit adjustments (reference_order IS NOT NULL) and legacy Fast Wholesale Entry
    # balance overrides must be excluded to prevent distorting historical balances.
    adjustments_agg = (
        CreditTransaction.objects.filter(
            transaction_type=CreditTransaction.TransactionType.ADJUSTMENT,
            created_at__date__gte=target_date,
            reference_order__isnull=True,  # standalone balance corrections only
        ).exclude(notes__icontains="Fast Wholesale Entry")
    )
    if customer_ids:
        adjustments_agg = adjustments_agg.filter(customer_id__in=customer_ids)
    adjustments_by_cust = {
        str(row["customer_id"]): (row["total"] or Decimal("0.00"))
        for row in adjustments_agg.values("customer_id").annotate(total=Sum("amount"))
    }

    results = {}
    for cid, cur_bal in cust_map.items():
        subsequent_orders = orders_by_cust.get(cid, Decimal("0.00"))
        subsequent_payments = payments_by_cust.get(cid, Decimal("0.00"))
        subsequent_adjs = adjustments_by_cust.get(cid, Decimal("0.00"))

        opening_due = cur_bal - subsequent_orders + subsequent_payments - subsequent_adjs
        results[cid] = str(opening_due.quantize(Decimal("0.01")))

    return results

