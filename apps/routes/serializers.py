from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
from .models import Route, Driver, DriverExpense, DriverShift
from apps.accounts.serializers import UserSerializer

class RouteSerializer(serializers.ModelSerializer):
    customer_count = serializers.SerializerMethodField()
    active_driver_name = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = [
            "id",
            "name",
            "code",
            "description",
            "is_active",
            "created_at",
            "updated_at",
            "customer_count",
            "active_driver_name",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "customer_count", "active_driver_name"]

    @extend_schema_field(OpenApiTypes.INT)
    def get_customer_count(self, obj):
        return obj.customers.filter(is_active=True).count()

    @extend_schema_field(OpenApiTypes.STR)
    def get_active_driver_name(self, obj):
        driver = obj.drivers.filter(is_active=True).first()
        if driver and driver.user:
            return driver.user.get_full_name() or driver.user.username
        return None


class DriverSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source="user", read_only=True)
    assigned_route_details = RouteSerializer(source="assigned_route", read_only=True)
    driver_name = serializers.SerializerMethodField()
    active_deliveries_count = serializers.SerializerMethodField()
    name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Driver
        fields = [
            "id",
            "user",
            "user_details",
            "assigned_route",
            "assigned_route_details",
            "driver_name",
            "active_deliveries_count",
            "name",
            "password",
            "phone_number",
            "vehicle_number",
            "license_number",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "user_details", "assigned_route_details", "driver_name", "active_deliveries_count"]

    @extend_schema_field(OpenApiTypes.STR)
    def get_driver_name(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return ""

    @extend_schema_field(OpenApiTypes.INT)
    def get_active_deliveries_count(self, obj):
        from django.utils import timezone
        from apps.deliveries.models import Delivery
        today = timezone.localdate()
        return Delivery.objects.filter(
            driver=obj,
            order__order_date=today,
            status__in=[Delivery.Status.ASSIGNED, Delivery.Status.IN_TRANSIT],
        ).count()

    def update(self, instance, validated_data):
        name = validated_data.pop("name", None)
        password = validated_data.pop("password", None)
        phone_number = validated_data.get("phone_number", None)

        if instance.user:
            user_changed = False
            if name is not None and name.strip():
                name_parts = name.strip().split(" ", 1)
                instance.user.first_name = name_parts[0]
                instance.user.last_name = name_parts[1] if len(name_parts) > 1 else ""
                user_changed = True
            if password is not None and password.strip():
                instance.user.set_password(password.strip())
                user_changed = True
            if phone_number is not None:
                instance.user.phone_number = phone_number.strip()
                user_changed = True
            if user_changed:
                instance.user.save()

        return super().update(instance, validated_data)


class CreateDriverSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        required=False,
        allow_null=True
    )
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Driver
        fields = [
            "id",
            "user",
            "name",
            "username",
            "password",
            "phone_number",
            "vehicle_number",
            "license_number",
            "assigned_route",
            "is_active",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        User = get_user_model()
        user = validated_data.pop("user", None)
        name = validated_data.pop("name", "").strip()
        username = validated_data.pop("username", "").strip()
        password = validated_data.pop("password", "").strip() or "zamzam123"
        phone_number = validated_data.get("phone_number", "").strip()

        if not user:
            if not name and not username:
                raise serializers.ValidationError({"name": "Driver name is required."})

            if not username:
                base_username = (name.lower().replace(" ", "_")) or "driver"
                base_username = "".join(c for c in base_username if c.isalnum() or c == "_")
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
            elif User.objects.filter(username=username).exists():
                raise serializers.ValidationError({"username": f"Username '{username}' is already in use."})

            name_parts = name.split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            user = User.objects.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                role=User.Role.DRIVER,
            )
            user.set_password(password)
            user.save()
        else:
            if hasattr(user, "driver_profile") and user.driver_profile:
                raise serializers.ValidationError({"user": "This user already has a driver profile."})

        driver = Driver.objects.create(user=user, **validated_data)
        return driver

    def to_representation(self, instance):
        return DriverSerializer(instance, context=self.context).data


class DriverExpenseSerializer(serializers.ModelSerializer):
    driver_name = serializers.SerializerMethodField()
    route_name = serializers.SerializerMethodField()
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = DriverExpense
        fields = [
            "id",
            "driver",
            "driver_name",
            "route_name",
            "category",
            "category_display",
            "custom_category",
            "amount",
            "date",
            "notes",
            "receipt_reference",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "driver", "driver_name", "route_name", "category_display", "created_by", "created_at", "updated_at"]

    @extend_schema_field(OpenApiTypes.STR)
    def get_driver_name(self, obj):
        if obj.driver and obj.driver.user:
            return obj.driver.user.get_full_name() or obj.driver.user.username
        return "General / Shop Expense"

    @extend_schema_field(OpenApiTypes.STR)
    def get_route_name(self, obj):
        if obj.driver and obj.driver.assigned_route:
            return obj.driver.assigned_route.name
        return "General / Shop"

    def validate_amount(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Expense amount must be greater than zero.")
        return value


class CreateDriverExpenseSerializer(serializers.ModelSerializer):
    driver = serializers.PrimaryKeyRelatedField(queryset=Driver.objects.all(), required=False, allow_null=True)

    class Meta:
        model = DriverExpense
        fields = [
            "id",
            "driver",
            "category",
            "custom_category",
            "amount",
            "date",
            "notes",
            "receipt_reference",
        ]
        read_only_fields = ["id"]

    def validate_amount(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Expense amount must be greater than zero.")
        return value


class DriverShiftSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source="driver.driver_name", read_only=True)
    route_name = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()

    class Meta:
        model = DriverShift
        fields = [
            "id",
            "driver",
            "driver_name",
            "route_name",
            "date",
            "is_opened",
            "opened_at",
            "kubbus_loaded",
            "romali_loaded",
            "opening_notes",
            "is_closed",
            "closed_at",
            "kubbus_returned",
            "romali_returned",
            "cash_collected",
            "upi_collected",
            "expenses_total",
            "net_cash_handover",
            "closing_notes",
            "metrics",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "driver",
            "driver_name",
            "route_name",
            "opened_at",
            "closed_at",
            "cash_collected",
            "upi_collected",
            "expenses_total",
            "net_cash_handover",
            "metrics",
            "created_at",
            "updated_at",
        ]

    def get_route_name(self, obj):
        if obj.driver and obj.driver.assigned_route:
            return obj.driver.assigned_route.name
        return "Unassigned"

    def get_metrics(self, obj):
        from apps.deliveries.models import Delivery
        from apps.payments.models import Payment
        from apps.routes.models import DriverExpense
        from django.db.models import Q, Sum

        deliveries = Delivery.objects.filter(
            Q(driver=obj.driver) | (Q(route=obj.driver.assigned_route) & Q(driver__isnull=True)),
            Q(order__order_date=obj.date) | Q(created_at__date=obj.date) | Q(status__in=[Delivery.Status.ASSIGNED, Delivery.Status.IN_TRANSIT, Delivery.Status.DELIVERED])
        ).select_related("order").prefetch_related("order__items__product").distinct()

        assigned_kubbus = 0
        assigned_romali = 0
        delivered_kubbus = 0
        delivered_romali = 0
        assigned_total_val = Decimal("0.00")

        for deliv in deliveries:
            assigned_total_val += deliv.order.total_amount
            is_deliv = deliv.status == Delivery.Status.DELIVERED
            for item in deliv.order.items.all():
                pname = item.product.name.lower()
                if "kub" in pname:
                    assigned_kubbus += item.quantity
                    if is_deliv:
                        delivered_kubbus += item.quantity
                elif "rom" in pname:
                    assigned_romali += item.quantity
                    if is_deliv:
                        delivered_romali += item.quantity

        payments = Payment.objects.filter(collected_by=obj.driver.user, received_at__date=obj.date)
        cash_col = payments.filter(payment_method="CASH").aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
        upi_col = payments.filter(payment_method="GPAY_UPI").aggregate(s=Sum("amount"))["s"] or Decimal("0.00")

        expenses = DriverExpense.objects.filter(driver=obj.driver, date=obj.date).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")

        delivered_count = deliveries.filter(status=Delivery.Status.DELIVERED).count()
        pending_count = deliveries.filter(status__in=[Delivery.Status.ASSIGNED, Delivery.Status.IN_TRANSIT]).count()

        return {
            "assigned_kubbus": assigned_kubbus,
            "assigned_romali": assigned_romali,
            "delivered_kubbus": delivered_kubbus,
            "delivered_romali": delivered_romali,
            "assigned_orders_count": deliveries.count(),
            "delivered_orders_count": delivered_count,
            "pending_orders_count": pending_count,
            "assigned_total_val": str(assigned_total_val),
            "today_cash_collected": str(cash_col),
            "today_upi_collected": str(upi_col),
            "today_expenses": str(expenses),
            "net_cash_in_hand": str(cash_col - expenses),
        }


class OpenDriverShiftSerializer(serializers.Serializer):
    kubbus_loaded = serializers.IntegerField(min_value=0, required=True)
    romali_loaded = serializers.IntegerField(min_value=0, required=True)
    opening_notes = serializers.CharField(required=False, allow_blank=True, default="")


class CloseDriverShiftSerializer(serializers.Serializer):
    kubbus_returned = serializers.IntegerField(min_value=0, required=False, default=0)
    romali_returned = serializers.IntegerField(min_value=0, required=False, default=0)
    closing_notes = serializers.CharField(required=False, allow_blank=True, default="")

