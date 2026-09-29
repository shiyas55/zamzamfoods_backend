from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Delivery
from apps.orders.serializers import OrderSerializer
from apps.routes.serializers import RouteSerializer, DriverSerializer

class DeliverySerializer(serializers.ModelSerializer):
    order_details = OrderSerializer(source="order", read_only=True)
    route_details = RouteSerializer(source="route", read_only=True)
    driver_name = serializers.SerializerMethodField()

    class Meta:
        model = Delivery
        fields = [
            "id",
            "delivery_number",
            "order",
            "order_details",
            "driver",
            "driver_name",
            "route",
            "route_details",
            "status",
            "delivered_at",
            "recipient_name",
            "failed_reason",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "delivery_number", "delivered_at", "created_at", "updated_at"]

    @extend_schema_field(OpenApiTypes.STR)
    def get_driver_name(self, obj):
        if obj.driver and obj.driver.user:
            return obj.driver.user.get_full_name() or obj.driver.user.username
        return ""


class CompleteDeliverySerializer(serializers.Serializer):
    recipient_name = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class NotDeliveredInputSerializer(serializers.Serializer):
    failed_reason = serializers.CharField(required=True, min_length=2, help_text="Reason why order could not be delivered")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class AssignDriverSerializer(serializers.Serializer):
    driver_id = serializers.UUIDField(required=True)
    allow_cross_route = serializers.BooleanField(required=False, default=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

