from rest_framework import serializers
from .models import ActivityLog, SystemSettings

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
            "is_maintenance_mode",
            "maintenance_message",
            "whatsapp_is_locked",
            "whatsapp_plan_name",
            "whatsapp_plan_expires_at",
            "whatsapp_license_key",
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
            "is_maintenance_mode",
            "maintenance_message",
            "whatsapp_is_locked",
            "whatsapp_plan_name",
            "whatsapp_plan_expires_at",
        ]
        read_only_fields = fields
