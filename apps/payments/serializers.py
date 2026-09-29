from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Payment
from apps.customers.serializers import CustomerSerializer
from apps.accounts.serializers import UserSerializer
from .services import record_payment_service

class PaymentSerializer(serializers.ModelSerializer):
    customer_details = CustomerSerializer(source="customer", read_only=True)
    collected_by_name = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    route_name = serializers.CharField(source="customer.route.name", read_only=True)
    payment_type = serializers.SerializerMethodField()
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    reversed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "id",
            "payment_number",
            "customer",
            "customer_name",
            "route_name",
            "customer_details",
            "order",
            "order_number",
            "payment_type",
            "amount",
            "payment_method",
            "status",
            "reference_number",
            "collected_by",
            "collected_by_name",
            "received_at",
            "notes",
            "reversed_by",
            "reversed_by_name",
            "reversed_at",
            "reversal_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "payment_number",
            "created_at",
            "updated_at",
            "collected_by_name",
            "payment_type",
            "order_number",
            "reversed_by",
            "reversed_by_name",
            "reversed_at",
            "reversal_reason",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_payment_type(self, obj):
        return "ORDER_PAYMENT" if obj.order_id else "PREVIOUS_CREDIT"

    @extend_schema_field(OpenApiTypes.STR)
    def get_collected_by_name(self, obj):
        if obj.collected_by:
            return obj.collected_by.get_full_name() or obj.collected_by.username
        return ""

    @extend_schema_field(OpenApiTypes.STR)
    def get_reversed_by_name(self, obj):
        if obj.reversed_by:
            return obj.reversed_by.get_full_name() or obj.reversed_by.username
        return ""


class ReversePaymentSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=3, help_text="Audit explanation for payment reversal")


class CreatePaymentSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    order_id = serializers.UUIDField(required=False, allow_null=True)
    payment_type = serializers.ChoiceField(choices=["ORDER_PAYMENT", "PREVIOUS_CREDIT"], required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    payment_method = serializers.ChoiceField(choices=Payment.Method.choices)
    reference_number = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    received_at = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        today = timezone.localdate()
        from apps.reports.models import DailyClosing
        closing = DailyClosing.objects.filter(date=today).first()
        if closing and closing.is_closed:
            raise serializers.ValidationError({"detail": f"Business day {today} is closed. Payments cannot be accepted."})
        if closing and not closing.is_opened:
            raise serializers.ValidationError({"detail": f"Business day {today} is not opened yet. Please open the day first."})

        customer_id = attrs.get("customer_id")
        order_id = attrs.get("order_id")
        payment_type = attrs.get("payment_type")

        if payment_type == "PREVIOUS_CREDIT":
            attrs["order_id"] = None
            order_id = None
        elif order_id and not payment_type:
            attrs["payment_type"] = "ORDER_PAYMENT"

        if order_id:
            from apps.orders.models import Order
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                raise serializers.ValidationError({"order_id": "Order does not exist."})
            if str(order.customer_id) != str(customer_id):
                raise serializers.ValidationError({"order_id": "Order does not belong to the specified customer."})

        request = self.context.get("request")
        if request and request.user.is_authenticated and request.user.role == "DRIVER":
            driver_profile = getattr(request.user, "driver_profile", None)
            if not driver_profile:
                raise serializers.ValidationError("User does not have an active driver profile.")

            from apps.customers.models import Customer
            try:
                customer = Customer.objects.get(id=customer_id)
            except Customer.DoesNotExist:
                raise serializers.ValidationError({"customer_id": "Customer does not exist."})

            if customer.route != driver_profile.assigned_route:
                raise serializers.ValidationError({
                    "customer_id": "Drivers can only collect payments for customers on their assigned route."
                })

            if order_id and order.driver != driver_profile:
                raise serializers.ValidationError({
                    "order_id": "Drivers can only collect payments for orders assigned to them."
                })

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None

        return record_payment_service(
            customer_id=validated_data["customer_id"],
            amount=validated_data["amount"],
            payment_method=validated_data["payment_method"],
            collected_by=user,
            order_id=validated_data.get("order_id"),
            reference_number=validated_data.get("reference_number", ""),
            notes=validated_data.get("notes", ""),
            received_at=validated_data.get("received_at"),
        )
