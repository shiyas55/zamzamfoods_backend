from django.db import models
from apps.common.models import TimeStampedUUIDModel


class WhatsAppAccount(TimeStampedUUIDModel):
    """
    Represents a Meta WhatsApp Business Account (WABA) phone number registration
    belonging to a specific shop/tenant.
    """
    shop = models.CharField(
        max_length=100,
        default="default",
        db_index=True,
        help_text="Tenant / Shop identifier"
    )
    waba_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Meta WhatsApp Business Account ID"
    )
    phone_number_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Meta WhatsApp Phone Number ID (used in webhooks and Cloud API)"
    )
    business_phone = models.CharField(
        max_length=30,
        blank=True,
        help_text="Sender / Business display phone number"
    )
    status = models.CharField(
        max_length=30,
        default="active",
        help_text="Account connection status"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "WhatsApp Account"
        verbose_name_plural = "WhatsApp Accounts"

    def __str__(self):
        return f"{self.business_phone or self.phone_number_id} ({self.shop}) - {self.status}"


class WhatsAppCustomer(TimeStampedUUIDModel):
    """
    Represents an external WhatsApp contact/user linked to a Zamzam customer shop.
    """
    shop = models.CharField(
        max_length=100,
        default="default",
        db_index=True,
        help_text="Tenant / Shop identifier"
    )
    whatsapp_phone = models.CharField(
        max_length=30,
        db_index=True,
        help_text="Standardized WhatsApp phone number (e.g. 919876543210)"
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whatsapp_profiles",
        help_text="Associated Zamzam Customer Shop"
    )
    name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Customer / Shop name"
    )
    profile_name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Meta WhatsApp profile push name"
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = [["shop", "whatsapp_phone"]]
        verbose_name = "WhatsApp Customer"
        verbose_name_plural = "WhatsApp Customers"

    def __str__(self):
        return f"{self.name or self.profile_name or self.whatsapp_phone} ({self.whatsapp_phone})"


class WhatsAppConversation(TimeStampedUUIDModel):
    """
    Active conversation thread between a WhatsApp customer and a shop.
    """
    shop = models.CharField(
        max_length=100,
        default="default",
        db_index=True,
        help_text="Tenant / Shop identifier"
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="whatsapp_conversations",
        help_text="Associated Zamzam Customer Shop"
    )
    whatsapp_phone = models.CharField(
        max_length=30,
        db_index=True,
        help_text="Customer phone number"
    )
    last_message = models.TextField(
        blank=True,
        help_text="Snippet of the latest message"
    )
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp of latest message"
    )
    unread_count = models.IntegerField(
        default=0,
        help_text="Count of unread incoming messages"
    )

    class Meta:
        ordering = ["-last_message_at", "-created_at"]
        unique_together = [["shop", "whatsapp_phone"]]
        verbose_name = "WhatsApp Conversation"
        verbose_name_plural = "WhatsApp Conversations"

    def __str__(self):
        cust_name = self.customer.name if self.customer else self.whatsapp_phone
        return f"Chat with {cust_name} ({self.whatsapp_phone}) [{self.shop}]"


class WhatsAppMessage(TimeStampedUUIDModel):
    """
    Individual message sent or received via the Meta WhatsApp Cloud API.
    """
    class Direction(models.TextChoices):
        INBOUND = "inbound", "Inbound"
        OUTBOUND = "outbound", "Outbound"

    class MessageType(models.TextChoices):
        TEXT = "text", "Text"
        IMAGE = "image", "Image"
        DOCUMENT = "document", "Document"
        AUDIO = "audio", "Audio"
        VOICE = "voice", "Voice"
        VIDEO = "video", "Video"
        OTHER = "other", "Other"

    conversation = models.ForeignKey(
        WhatsAppConversation,
        on_delete=models.CASCADE,
        related_name="messages",
        help_text="Conversation thread this message belongs to"
    )
    whatsapp_message_id = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        help_text="Unique Meta WhatsApp Message ID (wamid)"
    )
    direction = models.CharField(
        max_length=15,
        choices=Direction.choices,
        default=Direction.INBOUND,
        db_index=True
    )
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    text = models.TextField(
        blank=True,
        help_text="Text content or media caption"
    )
    media_id = models.CharField(
        max_length=150,
        blank=True,
        help_text="Meta media ID for images/documents/audio"
    )
    media_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Accessible media URL if cached"
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="Timestamp delivered by WhatsApp Cloud API"
    )
    raw_payload = models.JSONField(
        null=True,
        blank=True,
        help_text="Full raw webhook message JSON payload"
    )

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "WhatsApp Message"
        verbose_name_plural = "WhatsApp Messages"

    def __str__(self):
        return f"[{self.direction}] {self.message_type}: {self.text[:30]} ({self.timestamp:%H:%M})"
