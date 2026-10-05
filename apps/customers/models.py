from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.common.models import TimeStampedUUIDModel
from apps.routes.models import Route
from apps.products.models import Product

class Customer(TimeStampedUUIDModel):
    """
    Customer shop receiving daily deliveries of Kubbus and Romali.
    Approx. 200 shops distributed across delivery routes.
    """
    name = models.CharField(max_length=150, help_text="Shop or establishment name")
    owner_name = models.CharField(max_length=100, blank=True, help_text="Proprietor / store manager name")
    phone = models.CharField(max_length=20, help_text="Primary contact phone number")
    alternative_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(help_text="Street address / location")
    landmark = models.CharField(max_length=100, blank=True, help_text="Nearby landmark for delivery drivers")
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name="customers",
        help_text="Designated delivery route for this customer"
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("5000.00"),
        help_text="Maximum allowed outstanding credit"
    )
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Current outstanding balance owed by customer (receivable)"
    )
    notes = models.TextField(blank=True, help_text="Internal notes about shop or delivery preferences")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["route__name", "name"]
        verbose_name = "Customer Shop"
        verbose_name_plural = "Customer Shops"

    def __str__(self):
        return f"{self.name} - {self.route.name} (Bal: ₹{self.current_balance})"

    @property
    def is_credit_exceeded(self):
        return self.current_balance > self.credit_limit


class CustomerProductPrice(TimeStampedUUIDModel):
    """
    Customer-specific wholesale selling price for a product.
    Allows individual wholesale pricing for every shop (e.g. Shop A ₹10, Shop B ₹10.50).
    """
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="custom_prices",
        help_text="Customer shop receiving this negotiated price"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="customer_prices",
        help_text="Bakery product"
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Negotiated selling price in INR (always Decimal)"
    )
    effective_from = models.DateField(
        default=timezone.now,
        help_text="Date from which this price becomes active"
    )
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text="Optional expiry date for temporary promo pricing"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this custom price is currently in effect"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_customer_prices"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_customer_prices"
    )

    class Meta:
        ordering = ["customer__name", "product__name"]
        verbose_name = "Customer Product Price"
        verbose_name_plural = "Customer Product Prices"
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "product"],
                condition=models.Q(is_active=True),
                name="unique_active_customer_product_price"
            )
        ]

    def __str__(self):
        return f"{self.customer.name} - {self.product.name}: ₹{self.price}"


class CustomerDocument(TimeStampedUUIDModel):
    """
    Shop documents and multi-file storage (licenses, GST certificates, agreements, KYC, shop photos, etc.)
    """
    class DocumentType(models.TextChoices):
        FSSAI_LICENSE = "FSSAI_LICENSE", "FSSAI Food License"
        GST_CERTIFICATE = "GST_CERTIFICATE", "GST Certificate"
        TRADE_LICENSE = "TRADE_LICENSE", "Trade / Municipal License"
        RENT_AGREEMENT = "RENT_AGREEMENT", "Rent / Lease Agreement"
        ID_PROOF = "ID_PROOF", "Owner / Manager ID Proof"
        SHOP_PHOTO = "SHOP_PHOTO", "Shop Front / Location Photo"
        BANK_PROOF = "BANK_PROOF", "Bank Cheque / Passbook"
        CONTRACT = "CONTRACT", "Wholesale Supply Contract"
        OTHER = "OTHER", "Other Document"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="documents",
        help_text="Customer shop this document belongs to"
    )
    title = models.CharField(max_length=200, help_text="Title or name of document")
    document_type = models.CharField(
        max_length=40,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
        help_text="Category of the document"
    )
    file = models.FileField(
        upload_to="customer_documents/%Y/%m/",
        help_text="Uploaded document file (PDF, image, doc, etc.)"
    )
    file_name = models.CharField(max_length=255, blank=True, help_text="Original file name")
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    mime_type = models.CharField(max_length=100, blank=True, help_text="MIME type")
    document_number = models.CharField(max_length=100, blank=True, help_text="Optional document or registration number")
    expiry_date = models.DateField(null=True, blank=True, help_text="Optional expiry date for licenses/agreements")
    notes = models.TextField(blank=True, help_text="Optional notes or description")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_customer_documents"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Customer Document"
        verbose_name_plural = "Customer Documents"

    def __str__(self):
        return f"{self.customer.name} - {self.title} ({self.get_document_type_display()})"

