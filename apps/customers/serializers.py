from decimal import Decimal
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Customer, CustomerProductPrice
from apps.routes.serializers import RouteSerializer
from apps.products.models import Product

class CustomerProductPriceInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.00"))


class CustomerSerializer(serializers.ModelSerializer):
    route_details = RouteSerializer(source="route", read_only=True)
    is_credit_exceeded = serializers.BooleanField(read_only=True)
    credit_limit = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("5000.00"))
    product_prices = CustomerProductPriceInputSerializer(many=True, required=False, write_only=True)
    custom_prices = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "owner_name",
            "phone",
            "alternative_phone",
            "address",
            "landmark",
            "route",
            "route_details",
            "credit_limit",
            "current_balance",
            "notes",
            "is_credit_exceeded",
            "is_active",
            "product_prices",
            "custom_prices",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "current_balance", "is_credit_exceeded", "custom_prices", "created_at", "updated_at"]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_custom_prices(self, obj):
        prices = {}
        if hasattr(obj, "prefetched_custom_prices"):
            items = obj.prefetched_custom_prices
        else:
            from django.utils import timezone
            from django.db.models import Q
            today = timezone.localdate()
            items = obj.custom_prices.filter(
                is_active=True,
                effective_from__lte=today,
            ).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=today)
            ).order_by("effective_from", "created_at")
        for cp in items:
            if cp.price and Decimal(str(cp.price)) > Decimal("0.00"):
                prices[str(cp.product_id)] = str(cp.price)
        return prices

    def validate_credit_limit(self, value):
        if value is not None and value < Decimal("0.00"):
            raise serializers.ValidationError("Credit limit cannot be negative.")
        return value

    def create(self, validated_data):
        product_prices_data = validated_data.pop("product_prices", [])
        request = self.context.get("request")
        user = request.user if request else None

        from django.db import transaction
        with transaction.atomic():
            customer = super().create(validated_data)
            if product_prices_data:
                from .services import set_customer_product_price
                for item in product_prices_data:
                    set_customer_product_price(
                        customer=customer,
                        product_id=item["product_id"],
                        price=item["price"],
                        user=user,
                    )
            return customer

    def update(self, instance, validated_data):
        product_prices_data = validated_data.pop("product_prices", None)
        request = self.context.get("request")
        user = request.user if request else None

        from django.db import transaction
        with transaction.atomic():
            customer = super().update(instance, validated_data)
            if product_prices_data is not None:
                from .services import set_customer_product_price
                for item in product_prices_data:
                    set_customer_product_price(
                        customer=customer,
                        product_id=item["product_id"],
                        price=item["price"],
                        user=user,
                    )
            return customer


class CustomerProductPriceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    default_price = serializers.DecimalField(source="product.unit_price", max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CustomerProductPrice
        fields = [
            "id",
            "customer",
            "customer_name",
            "product",
            "product_name",
            "product_code",
            "default_price",
            "price",
            "effective_from",
            "effective_to",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "customer_name", "product_name", "product_code", "default_price", "created_at", "updated_at"]

    def validate_price(self, value):
        if value < Decimal("0.00"):
            raise serializers.ValidationError("Price cannot be negative.")
        return value


class SetCustomerPriceInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.00"))
    effective_from = serializers.DateField(required=False)
    effective_to = serializers.DateField(required=False, allow_null=True)


class CustomerPricingOverviewItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    product_code = serializers.CharField()
    packet_size = serializers.CharField()
    default_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    effective_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    has_custom_price = serializers.BooleanField()
    price_id = serializers.UUIDField(allow_null=True)
    is_active = serializers.BooleanField()


class CustomerDetailSummarySerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    customer_name = serializers.CharField()
    total_orders = serializers.IntegerField()
    total_sales = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=14, decimal_places=2)
    current_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit_limit = serializers.DecimalField(max_digits=14, decimal_places=2)
    is_credit_exceeded = serializers.BooleanField()
