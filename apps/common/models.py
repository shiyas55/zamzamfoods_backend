import uuid
from django.db import models

class TimeStampedUUIDModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created_at`` and ``updated_at`` fields, and a secure UUID primary key.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated"
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class ActivityLog(models.Model):
    """
    Immutable audit history recording critical operational business events.
    Tracks user, role, action, entity, snapshot summaries, and old/new values.
    """
    class EntityType(models.TextChoices):
        ORDER = "ORDER", "Order"
        PRICE = "PRICE", "Customer Price"
        PAYMENT = "PAYMENT", "Payment"
        DELIVERY = "DELIVERY", "Delivery"
        EXPENSE = "EXPENSE", "Driver Expense"
        CUSTOMER = "CUSTOMER", "Customer"
        PRODUCT = "PRODUCT", "Product"

    class ActionType(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        DELETED = "DELETED", "Deleted"
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
        PRICE_OVERRIDE = "PRICE_OVERRIDE", "Price Overridden"
        DELIVERED = "DELIVERED", "Delivered"
        NOT_DELIVERED = "NOT_DELIVERED", "Not Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs"
    )
    user_name = models.CharField(max_length=150, blank=True)
    user_role = models.CharField(max_length=50, blank=True)

    action = models.CharField(max_length=50, choices=ActionType.choices, db_index=True)
    entity_type = models.CharField(max_length=50, choices=EntityType.choices, db_index=True)
    entity_id = models.CharField(max_length=100, blank=True, db_index=True)
    entity_name = models.CharField(max_length=255, blank=True)

    summary = models.TextField(help_text="Human readable summary of the event")
    details = models.JSONField(default=dict, blank=True, help_text="Structured old/new values and metadata")

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Activity Log"
        verbose_name_plural = "Activity Logs"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["timestamp", "action"]),
        ]

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.user_name} ({self.user_role}): {self.summary}"


class SystemSettings(TimeStampedUUIDModel):
    """
    Singleton system configuration for Zamzam Foods.
    Stores company identity, tax information, contact numbers, and feature flags.
    Only administrators / owners can view full settings and modify them.
    """
    business_name = models.CharField(
        max_length=200,
        default="Zamzam Foods Wholesale",
        help_text="Official business/shop name displayed on bills and invoices"
    )
    phone_number = models.CharField(
        max_length=50,
        default="+91 98470 12345",
        help_text="Official business phone number"
    )
    gst_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="GSTIN / Tax Identification Number"
    )
    email = models.EmailField(
        blank=True,
        default="info@zamzamfoods.com",
        help_text="Business contact email"
    )
    address = models.TextField(
        blank=True,
        default="Main Road, Pandikkad, Malappuram, Kerala",
        help_text="Physical address of business / bakery facility"
    )
    upi_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="UPI ID (VPA) for digital customer payments (e.g. zamzam@okaxis)"
    )
    invoice_footer_notes = models.TextField(
        blank=True,
        default="Thank you for your business. Fresh Kubbus & Romali rotis delivered daily.",
        help_text="Footer remarks printed on bills and share messages"
    )

    # Operational Feature Toggles (Requested by Owner)
    is_whatsapp_enabled = models.BooleanField(
        default=True,
        help_text="Master toggle to enable or disable WhatsApp sharing options across the entire system"
    )
    is_self_order_enabled = models.BooleanField(
        default=True,
        help_text="Master toggle to enable or disable customer online self-ordering via public link"
    )
    is_order_discount_enabled = models.BooleanField(
        default=True,
        help_text="Master toggle to show or hide the 'Disc (₹)' column in Fast Wholesale Order Entry"
    )
    is_driver_module_enabled = models.BooleanField(
        default=True,
        help_text="Master toggle to enable or disable the entire Delivery Driver portion, driver mobile portal, routes driver dispatch, and driver performance tracking across the system"
    )
    is_maintenance_mode = models.BooleanField(
        default=False,
        help_text="Master toggle to put system under maintenance. When ON, only Admin/Owner can access."
    )
    maintenance_message = models.TextField(
        blank=True,
        default="System is currently undergoing scheduled maintenance. Please check back shortly.",
        help_text="Custom message displayed to staff and customers while maintenance mode is active"
    )

    # WhatsApp Upgrade Plan, Lock & License Key Settings
    whatsapp_is_locked = models.BooleanField(
        default=False,
        help_text="Lock status for WhatsApp feature. If True, requires upgrade key to unlock."
    )
    whatsapp_plan_name = models.CharField(
        max_length=100,
        default="WhatsApp Enterprise Pro",
        blank=True,
        help_text="Active plan name (e.g. Free Trial, Pro 30-Day, Annual License, Lifetime)"
    )
    whatsapp_plan_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration timestamp for WhatsApp plan. If expired, feature locks."
    )
    whatsapp_license_key = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Active license/upgrade key used to unlock or extend the plan"
    )

    # Security PIN Lock for Business Settings & System Controls
    settings_pin_code = models.CharField(
        max_length=10,
        default="7667",
        blank=True,
        help_text="4-digit security PIN to access Business Settings & System Controls (Default: 7667)"
    )

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return f"System Settings: {self.business_name} (Maintenance: {self.is_maintenance_mode}, WhatsApp: {self.is_whatsapp_enabled}, Locked: {self.whatsapp_is_locked})"

    @property
    def is_whatsapp_active(self):
        from django.utils import timezone
        if self.whatsapp_is_locked:
            return False
        if self.whatsapp_plan_expires_at and timezone.now() > self.whatsapp_plan_expires_at:
            return False
        return self.is_whatsapp_enabled

    @classmethod
    def get_settings(cls):
        """Returns the singleton settings instance, creating default if not exists."""
        settings_obj, _ = cls.objects.get_or_create(
            defaults={
                "business_name": "Zamzam Foods Wholesale",
                "phone_number": "+91 98470 12345",
                "gst_number": "",
                "email": "info@zamzamfoods.com",
                "address": "Main Road, Pandikkad, Malappuram, Kerala",
                "is_whatsapp_enabled": True,
                "is_self_order_enabled": True,
                "is_maintenance_mode": False,
                "maintenance_message": "System is currently undergoing scheduled maintenance. Please check back shortly.",
                "whatsapp_is_locked": False,
                "whatsapp_plan_name": "WhatsApp Enterprise Pro",
                "whatsapp_plan_expires_at": None,
                "whatsapp_license_key": "",
            }
        )
        return settings_obj


class BusinessDocument(TimeStampedUUIDModel):
    """
    Zamzam Foods own compliance and business documents.
    Stores FSSAI food safety license, GST certificate, trade license,
    FSSAI registration, insurance policies, bank documents, etc.
    Separate from CustomerDocument (which stores customer shop KYC docs).
    """
    from django.conf import settings as django_settings

    class DocumentType(models.TextChoices):
        FSSAI_LICENSE     = "FSSAI_LICENSE",     "FSSAI Food Safety License"
        GST_CERTIFICATE   = "GST_CERTIFICATE",   "GST Registration Certificate"
        TRADE_LICENSE     = "TRADE_LICENSE",     "Trade / Municipal License"
        SHOP_ACT          = "SHOP_ACT",          "Shop & Establishment Act"
        FIRE_NOC          = "FIRE_NOC",          "Fire NOC / Safety Certificate"
        POLLUTION_NOC     = "POLLUTION_NOC",     "Pollution Control NOC"
        BANK_DOCUMENT     = "BANK_DOCUMENT",     "Bank Account / Cheque"
        INSURANCE         = "INSURANCE",         "Business Insurance Policy"
        RENT_AGREEMENT    = "RENT_AGREEMENT",    "Rent / Lease Agreement"
        PAN_CARD          = "PAN_CARD",          "PAN Card"
        UDYAM             = "UDYAM",             "Udyam / MSME Registration"
        HALAL_CERT        = "HALAL_CERT",        "Halal Certification"
        QUALITY_CERT      = "QUALITY_CERT",      "Quality / ISO Certification"
        OTHER             = "OTHER",             "Other Document"

    title = models.CharField(max_length=200, help_text="Title or name of the document")
    document_type = models.CharField(
        max_length=40,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
        db_index=True,
    )
    file = models.FileField(
        upload_to="business_documents/%Y/%m/",
        help_text="Uploaded document file (PDF, image, etc.)"
    )
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(default=0, help_text="File size in bytes")
    mime_type = models.CharField(max_length=100, blank=True)
    document_number = models.CharField(
        max_length=150, blank=True,
        help_text="License / registration number (e.g. FSSAI 13325999000000)"
    )
    issuing_authority = models.CharField(
        max_length=200, blank=True,
        help_text="Issuing body or government authority"
    )
    issue_date = models.DateField(null=True, blank=True, help_text="Date of issue")
    expiry_date = models.DateField(null=True, blank=True, help_text="Expiry / renewal date")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, help_text="Mark document as active/inactive")
    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="uploaded_business_documents",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Business Document"
        verbose_name_plural = "Business Documents"

    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"
