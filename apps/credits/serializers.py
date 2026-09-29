from decimal import Decimal
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import CreditTransaction
from apps.customers.serializers import CustomerSerializer
from .services import record_adjustment_service

class CreditTransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    route_name = serializers.CharField(source="customer.route.name", read_only=True)
    recorded_by_name = serializers.SerializerMethodField()
    order_number = serializers.CharField(source="reference_order.order_number", read_only=True)
    payment_number = serializers.CharField(source="reference_payment.payment_number", read_only=True)

    balance_before = serializers.DecimalField(source="balance_before", max_digits=12, decimal_places=2, read_only=True)
    allocation = serializers.SerializerMethodField()

    class Meta:
        model = CreditTransaction
        fields = [
            "id",
            "customer",
            "customer_name",
            "route_name",
            "transaction_type",
            "amount",
            "balance_before",
            "balance_after",
            "allocation",
            "reference_order",
            "order_number",
            "reference_payment",
            "payment_number",
            "notes",
            "recorded_by",
            "recorded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "customer_name",
            "route_name",
            "recorded_by_name",
            "balance_before",
            "balance_after",
            "allocation",
            "order_number",
            "payment_number",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_allocation(self, obj):
        if obj.transaction_type == CreditTransaction.TransactionType.CREDIT_SALE or obj.reference_order_id:
            return "ORDER"
        if obj.transaction_type in [
            CreditTransaction.TransactionType.CASH_PAYMENT,
            CreditTransaction.TransactionType.GPAY_PAYMENT,
            CreditTransaction.TransactionType.ORDER_PAYMENT,
            CreditTransaction.TransactionType.PREVIOUS_CREDIT_PAYMENT,
        ]:
            return "ORDER_PAYMENT" if obj.reference_order_id else "PREVIOUS_CREDIT"
        if obj.transaction_type == CreditTransaction.TransactionType.PAYMENT_REVERSAL:
            return "REVERSAL"
        if obj.transaction_type == CreditTransaction.TransactionType.ADJUSTMENT:
            return "ADJUSTMENT"
        return "OPENING_BALANCE"

    @extend_schema_field(OpenApiTypes.STR)
    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return obj.recorded_by.get_full_name() or obj.recorded_by.username
        return "System"


class AdjustmentCreateSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    notes = serializers.CharField(required=True, min_length=5)

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None

        return record_adjustment_service(
            customer_id=validated_data["customer_id"],
            amount=validated_data["amount"],
            notes=validated_data["notes"],
            recorded_by=user,
        )
