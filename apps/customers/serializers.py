from decimal import Decimal
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Customer, CustomerProductPrice, CustomerDocument
from apps.routes.serializers import RouteSerializer
from apps.products.models import Product

class CustomerProductPriceInputSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.00"))


class CustomerSerializer(serializers.ModelSerializer):
    route_details = RouteSerializer(source="route", read_only=True)
    is_credit_exceeded = serializers.BooleanField(read_only=True)
    credit_limit = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("5000.00"))
    opening_balance = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, write_only=True)
    product_prices = CustomerProductPriceInputSerializer(many=True, required=False, write_only=True)
    custom_prices = serializers.SerializerMethodField(read_only=True)
    documents_count = serializers.IntegerField(source="documents.count", read_only=True)

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
            "opening_balance",
            "current_balance",
            "notes",
            "is_credit_exceeded",
            "is_active",
            "product_prices",
            "custom_prices",
            "documents_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "current_balance", "is_credit_exceeded", "custom_prices", "documents_count", "created_at", "updated_at"]

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
        opening_balance = validated_data.pop("opening_balance", None)
        product_prices_data = validated_data.pop("product_prices", [])
        request = self.context.get("request")
        user = request.user if request else None

        from django.db import transaction
        with transaction.atomic():
            customer = super().create(validated_data)
            if opening_balance is not None and Decimal(str(opening_balance)) > Decimal("0.00"):
                from apps.credits.services import record_opening_balance_service
                record_opening_balance_service(
                    customer=customer,
                    opening_balance=opening_balance,
                    recorded_by=user,
                )
            if product_prices_data:
                from .services import set_customer_product_price
                for item in product_prices_data:
                    set_customer_product_price(
                        customer=customer,
                        product_id=item["product_id"],
                        price=item["price"],
                        user=user,
                    )
            customer.refresh_from_db()
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


class CustomerDocumentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_route_name = serializers.CharField(source="customer.route.name", read_only=True)
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)
    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerDocument
        fields = [
            "id",
            "customer",
            "customer_name",
            "customer_route_name",
            "title",
            "document_type",
            "document_type_display",
            "file",
            "file_url",
            "file_name",
            "file_size",
            "mime_type",
            "document_number",
            "expiry_date",
            "notes",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "customer_name",
            "customer_route_name",
            "document_type_display",
            "file_url",
            "file_size",
            "mime_type",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
            "updated_at",
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

