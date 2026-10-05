from rest_framework import serializers
from .models import ActivityLog, SystemSettings, BusinessDocument

class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "user",
            "user_name",
            "user_role",
            "action",
            "entity_type",
            "entity_id",
            "entity_name",
            "summary",
            "details",
            "timestamp",
        ]
        read_only_fields = fields


class SystemSettingsSerializer(serializers.ModelSerializer):
    """
    Full settings serializer for Admin / Owner with full write access.
    """
    class Meta:
        model = SystemSettings
        fields = [
            "id",
            "business_name",
            "phone_number",
            "gst_number",
            "email",
            "address",
            "upi_id",
            "invoice_footer_notes",
            "is_whatsapp_enabled",
            "is_self_order_enabled",
            "is_order_discount_enabled",
            "is_driver_module_enabled",
            "is_maintenance_mode",
            "maintenance_message",
            "whatsapp_is_locked",
            "whatsapp_plan_name",
            "whatsapp_plan_expires_at",
            "whatsapp_license_key",
            "settings_pin_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PublicSystemSettingsSerializer(serializers.ModelSerializer):
    """
    Safe read-only settings serializer for customer links and receipts.
    """
    class Meta:
        model = SystemSettings
        fields = [
            "business_name",
            "phone_number",
            "gst_number",
            "email",
            "address",
            "upi_id",
            "invoice_footer_notes",
            "is_whatsapp_enabled",
            "is_self_order_enabled",
            "is_order_discount_enabled",
            "is_driver_module_enabled",
            "is_maintenance_mode",
            "maintenance_message",
            "whatsapp_is_locked",
            "whatsapp_plan_name",
            "whatsapp_plan_expires_at",
        ]
        read_only_fields = fields


class BusinessDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for Zamzam Foods own business compliance documents.
    """
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)

    class Meta:
        model = BusinessDocument
        fields = [
            "id",
            "title",
            "document_type",
            "document_type_display",
            "file",
            "file_url",
            "file_name",
            "file_size",
            "mime_type",
            "document_number",
            "issuing_authority",
            "issue_date",
            "expiry_date",
            "notes",
            "is_active",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "file_url", "file_size", "mime_type",
            "uploaded_by", "uploaded_by_name",
            "document_type_display", "created_at", "updated_at",
        ]

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.username
        return None
