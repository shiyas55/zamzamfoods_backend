from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Order, OrderItem
from apps.customers.serializers import CustomerSerializer
from apps.products.serializers import ProductSerializer
from apps.routes.serializers import RouteSerializer, DriverSerializer
from .services import create_order_service, update_order_service, _UNSET

class OrderItemSerializer(serializers.ModelSerializer):
    product_details = ProductSerializer(source="product", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_details",
            "quantity",
            "unit_price",
            "subtotal",
        ]
        read_only_fields = ["id", "subtotal"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_details = CustomerSerializer(source="customer", read_only=True)
    route_details = RouteSerializer(source="route", read_only=True)
    driver_name = serializers.SerializerMethodField()
    delivery_status = serializers.SerializerMethodField()
    delivery_id = serializers.SerializerMethodField()
    previous_balance = serializers.SerializerMethodField()
    balance_after = serializers.SerializerMethodField()
    paid_amount = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer",
            "customer_details",
            "route",
            "route_details",
            "driver",
            "driver_name",
            "order_date",
            "status",
            "total_amount",
            "shop_expense",
            "shop_expense_notes",
            "notes",
            "items",
            "delivery_status",
            "delivery_id",
            "source",
            "entered_by_role",
            "entered_by_name",
            "created_at",
            "updated_at",
            "submitted_at",
            "previous_balance",
            "balance_after",
            "paid_amount",
        ]
        read_only_fields = [
            "id",
            "order_number",
            "total_amount",
            "created_at",
            "updated_at",
            "submitted_at",
            "source",
            "entered_by_role",
            "entered_by_name",
            "previous_balance",
            "balance_after",
            "paid_amount",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_driver_name(self, obj):
        if obj.driver and obj.driver.user:
            return obj.driver.user.get_full_name() or obj.driver.user.username
        return "Unassigned"

    @extend_schema_field(OpenApiTypes.STR)
    def get_delivery_status(self, obj):
        if hasattr(obj, "delivery") and obj.delivery:
            return obj.delivery.status
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_delivery_id(self, obj):
        if hasattr(obj, "delivery") and obj.delivery:
            return str(obj.delivery.id)
        return None

    @extend_schema_field(OpenApiTypes.STR)
    def get_previous_balance(self, obj):
        has_prefetched = hasattr(obj, "_prefetched_objects_cache") and "credit_ledger_entries" in obj._prefetched_objects_cache
        if has_prefetched:
            tx = next((t for t in obj.credit_ledger_entries.all() if t.transaction_type == "CREDIT_SALE"), None)
        else:
            tx = obj.credit_ledger_entries.filter(transaction_type="CREDIT_SALE").first()

        if tx:
            return str(tx.balance_before)

        from apps.credits.models import CreditTransaction
        prior_tx = CreditTransaction.objects.filter(
            customer_id=obj.customer_id,
            created_at__lt=obj.created_at
        ).order_by("-created_at").first()
        if prior_tx:
            return str(prior_tx.balance_after)

        return "0.00"

    @extend_schema_field(OpenApiTypes.STR)
    def get_balance_after(self, obj):
        has_prefetched = hasattr(obj, "_prefetched_objects_cache") and "credit_ledger_entries" in obj._prefetched_objects_cache
        if has_prefetched:
            tx = next((t for t in obj.credit_ledger_entries.all() if t.transaction_type == "CREDIT_SALE"), None)
        else:
            tx = obj.credit_ledger_entries.filter(transaction_type="CREDIT_SALE").first()

        if tx:
            return str(tx.balance_after)

        prev_bal = Decimal(self.get_previous_balance(obj))
        tot = Decimal(str(obj.total_amount or "0.00"))
        return str((prev_bal + tot).quantize(Decimal("0.01")))

    @extend_schema_field(OpenApiTypes.STR)
    def get_paid_amount(self, obj):
        has_prefetched = hasattr(obj, "_prefetched_objects_cache") and "payments" in obj._prefetched_objects_cache
        if has_prefetched:
            payments = obj.payments.all()
        else:
            from apps.payments.models import Payment
            payments = Payment.objects.filter(order=obj)
        total_p = sum((Decimal(str(p.amount)) for p in payments), Decimal("0.00"))
        return str(total_p.quantize(Decimal("0.01")))


class OrderItemCreateInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=Decimal("0.00"))


class CreateOrderSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    driver_id = serializers.UUIDField(required=False, allow_null=True)
    order_date = serializers.DateField(required=False)
    shop_expense = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"), min_value=Decimal("0.00"))
    shop_expense_notes = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    source = serializers.ChoiceField(choices=["MANAGER", "OWNER", "CUSTOMER_LINK"], required=False, default="MANAGER")
    entered_by_role = serializers.CharField(required=False, allow_blank=True, default="")
    entered_by_name = serializers.CharField(required=False, allow_blank=True, default="")
    entered_by_type = serializers.CharField(required=False, allow_blank=True, default="MANAGER")
    order_number = serializers.CharField(required=False, allow_blank=True, default="")
    items = OrderItemCreateInputSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must have at least one item.")
        return value

    def validate(self, attrs):
        order_date = attrs.get("order_date")
        if not order_date:
            order_date = timezone.localdate()
        attrs["order_date"] = order_date

        source = attrs.get("source", "MANAGER")
        # Online customer self-orders can be placed anytime without requiring pre-opened daily sheet
        if source == "CUSTOMER_LINK":
            from apps.common.models import SystemSettings
            sys_settings = SystemSettings.get_settings()
            if not sys_settings.is_self_order_enabled:
                raise serializers.ValidationError({"detail": f"Online customer self-ordering is currently turned off by the shop administration. Please contact {sys_settings.phone_number} directly."})
            return attrs

        from apps.reports.models import DailyClosing
        closing = DailyClosing.objects.filter(date=order_date).first()
        if closing and closing.is_closed:
            raise serializers.ValidationError({"detail": f"Business day {order_date} is closed. Data entry is not allowed."})
        if closing and not closing.is_opened:
            raise serializers.ValidationError({"detail": f"Business day {order_date} has not been opened yet. You must open the day before entering orders."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None

        items_data = validated_data["items"]
        customer_id = validated_data["customer_id"]
        driver_id = validated_data.get("driver_id") if "driver_id" in validated_data else _UNSET
        order_date = validated_data.get("order_date")
        shop_expense = validated_data.get("shop_expense", Decimal("0.00"))
        shop_expense_notes = validated_data.get("shop_expense_notes", "")
        notes = validated_data.get("notes", "")
        order_number = validated_data.get("order_number", "").strip() or None

        return create_order_service(
            customer_id=customer_id,
            items_data=items_data,
            order_date=order_date,
            driver_id=driver_id,
            shop_expense=shop_expense,
            shop_expense_notes=shop_expense_notes,
            notes=notes,
            created_by=user,
            source=validated_data.get("source", "MANAGER"),
            entered_by_role=validated_data.get("entered_by_role", ""),
            entered_by_name=validated_data.get("entered_by_name", ""),
            entered_by_type=validated_data.get("entered_by_type", "MANAGER"),
            order_number=order_number,
        )


class UpdateOrderSerializer(serializers.Serializer):
    items = OrderItemCreateInputSerializer(many=True, required=False)
    driver_id = serializers.UUIDField(required=False, allow_null=True)
    route_id = serializers.UUIDField(required=False, allow_null=True)
    shop_expense = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=Decimal("0.00"))
    shop_expense_notes = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        instance = self.instance
        if instance:
            if instance.status in ["DELIVERED", "COMPLETED", "CANCELLED"]:
                raise serializers.ValidationError({"detail": f"Cannot edit order #{instance.order_number} because it is already {instance.get_status_display()}."})
            if hasattr(instance, "delivery") and instance.delivery and instance.delivery.status == "DELIVERED":
                raise serializers.ValidationError({"detail": f"Cannot edit order #{instance.order_number} because it is already Delivered."})

            order_date = instance.order_date
            from apps.reports.models import DailyClosing
            closing = DailyClosing.objects.filter(date=order_date).first()
            if closing and closing.is_closed:
                raise serializers.ValidationError({"detail": f"Business day {order_date} is closed. Data modification is not allowed."})
            if closing and not closing.is_opened:
                raise serializers.ValidationError({"detail": f"Business day {order_date} has not been opened yet. You must open the day before modifying orders."})
        return attrs

    def update(self, instance, validated_data):
        request = self.context.get("request")
        user = request.user if request else None

        items_data = validated_data.get("items")
        driver_id = validated_data.get("driver_id")
        route_id = validated_data.get("route_id")
        shop_expense = validated_data.get("shop_expense")
        shop_expense_notes = validated_data.get("shop_expense_notes")
        notes = validated_data.get("notes")

        try:
            return update_order_service(
                order_id=instance.id,
                items_data=items_data,
                driver_id=driver_id,
                route_id=route_id,
                shop_expense=shop_expense,
                shop_expense_notes=shop_expense_notes,
                notes=notes,
                user=user,
            )
        except ValueError as e:
            raise serializers.ValidationError({"detail": str(e)})

