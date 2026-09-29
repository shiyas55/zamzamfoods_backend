from decimal import Decimal
from django.db import models
from apps.common.models import TimeStampedUUIDModel

class Product(TimeStampedUUIDModel):
    """
    Bakery products manufactured and distributed by Zamzam Foods.
    Initially Kubbus and Romali, expandable to new products later.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Product name (e.g. Kubbus, Romali)")
    code = models.CharField(max_length=20, unique=True, help_text="Product SKU or identifier (e.g. KUB, ROM)")
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Standard unit selling price in INR (e.g. 35.00)"
    )
    packet_size = models.CharField(
        max_length=50,
        blank=True,
        help_text="Packaging specification (e.g. 10 pcs / pack)"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return f"{self.name} (₹{self.unit_price})"
