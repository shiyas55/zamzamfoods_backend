import _markupbase
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.permissions import IsManagerOrOwner, IsOwner, IsAssignedDriverOrManagerOwner
from .models import Route, Driver, DriverExpense, DriverShift
from .serializers import (
    RouteSerializer,
    DriverSerializer,
    CreateDriverSerializer,
    DriverExpenseSerializer,
    CreateDriverExpenseSerializer,
    DriverShiftSerializer,
    OpenDriverShiftSerializer,
    CloseDriverShiftSerializer,
)

class RouteViewSet(viewsets.ModelViewSet):
    """
    CRUD for delivery routes.
    - Owner/Manager: Full access to all routes.
    - Driver: Isolated to their assigned route only.
    """
    serializer_class = RouteSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsOwner()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Route.objects.none()

        if user.is_superuser or user.role in ["OWNER", "MANAGER"]:
            return Route.objects.all().order_by("name")

        if user.role == "DRIVER":
            # Isolate to driver's assigned route
            if hasattr(user, "driver_profile") and user.driver_profile and user.driver_profile.assigned_route:
                return Route.objects.filter(id=user.driver_profile.assigned_route_id)
            return Route.objects.none()

        return Route.objects.none()


class DriverViewSet(viewsets.ModelViewSet):
    """
    Driver profile management.
    - Owner: Full access to create, update, delete drivers.
    - Manager: View drivers.
    - Driver: Data isolated to only their own driver profile.
    """
    serializer_class = DriverSerializer

    def get_permissions(self):
        if self.action in ["create", "destroy", "update", "partial_update"]:
            return [IsManagerOrOwner()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateDriverSerializer
        return DriverSerializer

    def perform_create(self, serializer):
        driver = serializer.save()
        from apps.common.audit import log_activity
        log_activity(
            user=self.request.user,
            action="CREATED",
            entity_type="DRIVER",
            entity_id=driver.id,
            entity_name=driver.driver_name,
            summary=f"Created driver profile for {driver.driver_name}",
            details={
                "username": driver.user.username if driver.user else "",
                "route": driver.assigned_route.name if driver.assigned_route else "Unassigned",
                "vehicle": driver.vehicle_number,
            },
        )

    def perform_update(self, serializer):
        driver = serializer.save()
        from apps.common.audit import log_activity
        log_activity(
            user=self.request.user,
            action="UPDATED",
            entity_type="DRIVER",
            entity_id=driver.id,
            entity_name=driver.driver_name,
            summary=f"Updated driver profile for {driver.driver_name}",
            details={
                "route": driver.assigned_route.name if driver.assigned_route else "Unassigned",
                "vehicle": driver.vehicle_number,
                "phone": driver.phone_number,
            },
        )

    def perform_destroy(self, instance):
        from apps.common.audit import log_activity
        log_activity(
            user=self.request.user,
            action="DELETED",
            entity_type="DRIVER",
            entity_id=instance.id,
            entity_name=instance.driver_name,
            summary=f"Deleted driver profile for {instance.driver_name}",
        )
        instance.delete()

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Driver.objects.none()

        if user.is_superuser or user.role in ["OWNER", "MANAGER"]:
            return Driver.objects.select_related("user", "assigned_route").all()

        if user.role == "DRIVER":
            # Strict driver isolation
            return Driver.objects.select_related("user", "assigned_route").filter(user=user)

        return Driver.objects.none()

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def my_profile(self, request):
        """
        Convenience endpoint for the logged-in driver to retrieve their assigned profile and route.
        """
        if hasattr(request.user, "driver_profile") and request.user.driver_profile:
            serializer = self.get_serializer(request.user.driver_profile)
            return Response(serializer.data)
        return Response(
            {"error": "No driver profile associated with this account."},
            status=status.HTTP_404_NOT_FOUND
        )


class DriverExpenseViewSet(viewsets.ModelViewSet):
    """
    Endpoints for Driver operating expenses (fuel, food, tolls, repairs).
    - Drivers can only see, create, and manage their OWN expenses.
    - Owner and Manager can audit all driver expenses with route and category filters.
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["notes", "receipt_reference", "custom_category", "driver__user__first_name", "driver__user__username"]
    ordering_fields = ["date", "amount", "created_at"]

    def get_permissions(self):
        return [permissions.IsAuthenticated(), IsAssignedDriverOrManagerOwner()]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateDriverExpenseSerializer
        return DriverExpenseSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return DriverExpense.objects.none()

        queryset = DriverExpense.objects.select_related("driver", "driver__user", "driver__assigned_route", "created_by")

        # Filters for Managers and Owners
        driver_id = self.request.query_params.get("driver")
        if driver_id:
            queryset = queryset.filter(driver_id=driver_id)

        route_id = self.request.query_params.get("route")
        if route_id:
            queryset = queryset.filter(driver__assigned_route_id=route_id)

        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        date_param = self.request.query_params.get("date")
        if date_param:
            queryset = queryset.filter(date=date_param)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        if user.is_superuser or user.role in ["OWNER", "MANAGER"]:
            return queryset.order_by("-date", "-created_at")

        # Strict Driver Data Isolation
        if user.role == "DRIVER":
            return queryset.filter(driver__user=user).order_by("-date", "-created_at")

        return DriverExpense.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == "DRIVER":
            driver = getattr(user, "driver_profile", None)
            if not driver:
                raise permissions.exceptions.PermissionDenied("User does not have an active driver profile.")
            instance = serializer.save(driver=driver, created_by=user)
        else:
            # Manager or owner creating expense (driver is optional for shop/general expenses)
            instance = serializer.save(created_by=user)

        from apps.common.audit import log_activity
        log_activity(
            user=user,
            action="CREATED",
            entity_type="EXPENSE",
            entity_id=instance.id,
            entity_name=f"{instance.get_category_display()} Expense",
            summary=f"{user.get_full_name() or user.username} logged {instance.get_category_display()} expense of ₹{instance.amount}",
            details={
                "category": instance.category,
                "amount": str(instance.amount),
                "date": str(instance.date),
                "notes": instance.notes,
            },
        )

    def perform_update(self, serializer):
        user = self.request.user
        if user.role == "DRIVER":
            driver = getattr(user, "driver_profile", None)
            serializer.save(driver=driver)
        else:
            serializer.save()

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def summary(self, request):
        """
        Calculates today's, this week's, and category breakdown of driver expenses.
        """
        today = timezone.localdate()
        week_start = today - timezone.timedelta(days=today.weekday())

        qs = self.get_queryset()

        today_qs = qs.filter(date=today)
        week_qs = qs.filter(date__gte=week_start, date__lte=today)

        today_total = today_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        week_total = week_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        all_total = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Category breakdown for today
        categories = {}
        for cat_code, cat_label in DriverExpense.Category.choices:
            cat_sum = today_qs.filter(category=cat_code).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            categories[cat_code] = {
                "label": cat_label,
                "total": cat_sum,
            }

        return Response({
            "date": today,
            "today_total": today_total,
            "week_total": week_total,
            "all_total": all_total,
            "today_categories": categories,
            "today_count": today_qs.count(),
        })


class DriverShiftViewSet(viewsets.ModelViewSet):
    """
    Driver daily shift tracking: Day Open (stock check & takeover of Kubbus & Romali ps)
    and Day Closing (reconciliation of stock, collections, and handovers).
    """
    serializer_class = DriverShiftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return DriverShift.objects.none()
        if user.is_superuser or user.role in ["OWNER", "MANAGER"]:
            return DriverShift.objects.select_related("driver", "driver__user", "driver__assigned_route").all()
        if user.role == "DRIVER":
            return DriverShift.objects.select_related("driver", "driver__user", "driver__assigned_route").filter(driver__user=user)
        return DriverShift.objects.none()

    @action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def today(self, request):
        user = request.user
        driver = getattr(user, "driver_profile", None)
        if not driver:
            driver_id = request.query_params.get("driver_id")
            if driver_id:
                driver = Driver.objects.filter(id=driver_id).first()
            if not driver:
                driver = Driver.objects.first()

        if not driver:
            return Response({"error": "No driver profile found"}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.localdate()
        shift, _ = DriverShift.objects.get_or_create(
            driver=driver,
            date=today,
        )
        serializer = self.get_serializer(shift)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def open_day(self, request):
        user = request.user
        driver = getattr(user, "driver_profile", None)
        if not driver:
            driver_id = request.data.get("driver_id")
            if driver_id and (user.is_superuser or user.role in ["OWNER", "MANAGER"]):
                driver = Driver.objects.filter(id=driver_id).first()
            if not driver:
                driver = Driver.objects.first()
            if not driver:
                return Response({"error": "Driver profile required to open shift"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OpenDriverShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        today = timezone.localdate()
        shift, _ = DriverShift.objects.get_or_create(
            driver=driver,
            date=today,
        )

        shift.is_opened = True
        shift.opened_at = timezone.now()
        shift.kubbus_loaded = serializer.validated_data["kubbus_loaded"]
        shift.romali_loaded = serializer.validated_data["romali_loaded"]
        shift.opening_notes = serializer.validated_data.get("opening_notes", "")
        shift.opening_notes = serializer.validated_data.get("opening_notes", "")
        shift.save()

        # Auto-create deliveries for submitted orders assigned to this driver
        from apps.orders.models import Order
        from apps.deliveries.models import Delivery
        
        pending_orders = Order.objects.filter(
            driver=driver,
            order_date=today,
            status__in=[Order.Status.SUBMITTED, Order.Status.LOCKED],
            delivery__isnull=True
        )
        
        delivery_count = 0
        for order in pending_orders:
            count = Delivery.objects.filter(delivery_number__startswith=f"DEL-{today.strftime('%Y%m%d')}").count() + 1
            del_number = f"DEL-{today.strftime('%Y%m%d')}-{count:04d}"
            while Delivery.objects.filter(delivery_number=del_number).exists():
                count += 1
                del_number = f"DEL-{today.strftime('%Y%m%d')}-{count:04d}"
            
            delivery_obj, created = Delivery.objects.get_or_create(
                order=order,
                defaults={
                    "delivery_number": del_number,
                    "driver": driver,
                    "route": order.route,
                    "status": Delivery.Status.ASSIGNED
                }
            )
            order.status = Order.Status.DELIVERY_CREATED
            order.save(update_fields=["status", "updated_at"])
            if created:
                delivery_count += 1

        from apps.common.audit import log_activity
        log_activity(
            user=user,
            action="OPENED",
            entity_type="DRIVER_SHIFT",
            entity_id=shift.id,
            entity_name=f"{driver.driver_name} Shift",
            summary=f"{driver.driver_name} opened shift: confirmed {shift.kubbus_loaded} Kubbus, {shift.romali_loaded} Romali. Auto-dispatched {delivery_count} orders.",
            details={
                "kubbus_loaded": shift.kubbus_loaded,
                "romali_loaded": shift.romali_loaded,
                "notes": shift.opening_notes,
                "dispatched_orders": delivery_count,
            },
        )

        return Response(self.get_serializer(shift).data)

    @action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def close_day(self, request):
        user = request.user
        driver = getattr(user, "driver_profile", None)
        if not driver:
            driver_id = request.data.get("driver_id")
            if driver_id and (user.is_superuser or user.role in ["OWNER", "MANAGER"]):
                driver = Driver.objects.filter(id=driver_id).first()
            if not driver:
                driver = Driver.objects.first()
            if not driver:
                return Response({"error": "Driver profile required to close shift"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CloseDriverShiftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        today = timezone.localdate()
        shift, _ = DriverShift.objects.get_or_create(
            driver=driver,
            date=today,
        )

        from apps.payments.models import Payment
        from apps.routes.models import DriverExpense

        payments = Payment.objects.filter(collected_by=driver.user, received_at__date=today)
        cash_col = payments.filter(payment_method="CASH").aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
        upi_col = payments.filter(payment_method="GPAY_UPI").aggregate(s=Sum("amount"))["s"] or Decimal("0.00")
        expenses = DriverExpense.objects.filter(driver=driver, date=today).aggregate(s=Sum("amount"))["s"] or Decimal("0.00")

        shift.is_closed = True
        shift.closed_at = timezone.now()
        shift.kubbus_returned = serializer.validated_data.get("kubbus_returned", 0)
        shift.romali_returned = serializer.validated_data.get("romali_returned", 0)
        shift.cash_collected = cash_col
        shift.upi_collected = upi_col
        shift.expenses_total = expenses
        shift.net_cash_handover = cash_col - expenses
        shift.closing_notes = serializer.validated_data.get("closing_notes", "")
        shift.save()

        from apps.common.audit import log_activity
        log_activity(
            user=user,
            action="CLOSED",
            entity_type="DRIVER_SHIFT",
            entity_id=shift.id,
            entity_name=f"{driver.driver_name} Shift",
            summary=f"{driver.driver_name} closed shift: Cash ₹{cash_col}, UPI ₹{upi_col}, Net Cash Handover ₹{shift.net_cash_handover}",
            details={
                "cash_collected": str(cash_col),
                "upi_collected": str(upi_col),
                "expenses_total": str(expenses),
                "net_cash_handover": str(shift.net_cash_handover),
                "kubbus_returned": shift.kubbus_returned,
                "romali_returned": shift.romali_returned,
            },
        )

        return Response(self.get_serializer(shift).data)

