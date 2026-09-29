from rest_framework import serializers
from .models import WhatsAppConversation, WhatsAppMessage, WhatsAppCustomer
from apps.customers.models import Customer


class WhatsAppCustomerMiniSerializer(serializers.ModelSerializer):
    route_name = serializers.CharField(source="route.name", read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "owner_name",
            "phone",
            "alternative_phone",
            "route_name",
            "current_balance",
        ]


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppMessage
        fields = [
            "id",
            "whatsapp_message_id",
            "direction",
            "message_type",
            "text",
            "media_id",
            "media_url",
            "timestamp",
            "created_at",
        ]
        read_only_fields = fields


class WhatsAppConversationListSerializer(serializers.ModelSerializer):
    customer = WhatsAppCustomerMiniSerializer(read_only=True)
    contact_name = serializers.SerializerMethodField()

    class Meta:
        model = WhatsAppConversation
        fields = [
            "id",
            "shop",
            "whatsapp_phone",
            "last_message",
            "last_message_at",
            "unread_count",
            "customer",
            "contact_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_contact_name(self, obj):
        if obj.customer and obj.customer.name:
            return obj.customer.name
        # Check WhatsAppCustomer profile
        profile = WhatsAppCustomer.objects.filter(shop=obj.shop, whatsapp_phone=obj.whatsapp_phone).first()
        if profile and profile.name:
            return profile.name
        if profile and profile.profile_name:
            return profile.profile_name
        return f"+{obj.whatsapp_phone}" if obj.whatsapp_phone else "Unknown Contact"


class WhatsAppConversationDetailSerializer(WhatsAppConversationListSerializer):
    messages = WhatsAppMessageSerializer(many=True, read_only=True)

    class Meta(WhatsAppConversationListSerializer.Meta):
        fields = WhatsAppConversationListSerializer.Meta.fields + ["messages"]
