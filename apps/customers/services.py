from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from apps.products.models import Product
from .models import Customer, CustomerProductPrice

def get_effective_product_price(customer, product):
    """
    Determines effective selling price for a customer and product:
    1. Checks active CustomerProductPrice for this (customer, product).
    2. Falls back to product.unit_price if no custom price exists.
    Returns: (price: Decimal, is_custom: bool, price_record_id: Optional[str])
    """
    custom_price_obj = CustomerProductPrice.objects.filter(
        customer=customer,
        product=product,
        is_active=True
    ).order_by("-effective_from", "-created_at").first()

    if custom_price_obj:
        return custom_price_obj.price, True, str(custom_price_obj.id)
    return product.unit_price, False, None


def set_customer_product_price(customer=None, product=None, price=None, effective_from=None, effective_to=None, user=None, customer_id=None, product_id=None):
    """
    Configures or updates customer-specific wholesale price for a product.
    Deactivates any previous active price for this customer+product.
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
