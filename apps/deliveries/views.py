from django.db import IntegrityError
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.permissions import IsAssignedDriverOrManagerOwner, IsManagerOrOwner
from .models import Delivery
from apps.orders.models import Order
from .serializers import DeliverySerializer, CompleteDeliverySerializer
from .services import complete_delivery_service

class DeliveryViewSet(viewsets.ModelViewSet):
    """
    CRUD and actions for delivery dispatches.
    - Owner & Manager: Full visibility across all routes and drivers.
    - Driver: Strictly isolated to deliveries assigned to this driver!
    """
    serializer_class = DeliverySerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["delivery_number", "order__order_number", "order__customer__name"]
    ordering_fields = ["created_at", "delivered_at", "status"]

    def get_permissions(self):
        if self.action in ["create", "destroy", "update", "partial_update"]:
            return [IsManagerOrOwner()]
        return [permissions.IsAuthenticated(), IsAssignedDriverOrManagerOwner()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Delivery.objects.none()

        queryset = Delivery.objects.select_related(
            "order",
            "order__customer",
            "order__customer__route",
            "driver",
            "driver__user",
            "route",
        ).prefetch_related("order__items__product")

        # Filters for managers/owners
        route_id = self.request.query_params.get("route")
        if route_id:
            queryset = queryset.filter(route_id=route_id)

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        date_param = self.request.query_params.get("date")
        if date_param:
            queryset = queryset.filter(order__order_date=date_param)

        if user.is_superuser or user.role in ["OWNER", "MANAGER"]:
            return queryset.order_by("-created_at").distinct()

        # Strict Driver Data Isolation:
        # Driver A will NEVER see or retrieve Driver B's deliveries.
        if user.role == "DRIVER":
            return queryset.filter(driver__user=user).order_by("-created_at").distinct()

        return Delivery.objects.none()

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            delivery = serializer.save()
            
            # Update order status to DELIVERY_CREATED
            order = delivery.order
            order.status = Order.Status.DELIVERY_CREATED
            order.save(update_fields=["status"])
            
            # Audit log
            from apps.orders.models import OrderActivityLog
            OrderActivityLog.objects.create(
                order=order,
                action=f"Delivery Created (No: {delivery.delivery_number})",
                user_name=request.user.get_full_name() or request.user.username,
                user_role=request.user.role,
                source="MANAGER",
                details={"delivery_number": delivery.delivery_number}
            )
            
            return Response(DeliverySerializer(delivery).data, status=status.HTTP_201_CREATED)
        except IntegrityError:
            # Catch duplicate delivery due to OneToOneField on Order
            order_id = request.data.get("order")
            existing_delivery = Delivery.objects.filter(order_id=order_id).first()
            if existing_delivery:
                return Response(
                    {"detail": "DELIVERY ALREADY CREATED", "delivery_id": str(existing_delivery.id), "delivery_number": existing_delivery.delivery_number}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response({"detail": "A database integrity error occurred."}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        """
        Action for driver to mark a delivery as completed.
        Atomically updates delivery status and records credit sale in customer ledger.
        """
        delivery = self.get_object()  # Verifies driver isolation & permission!
        serializer = CompleteDeliverySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient_name = serializer.validated_data.get("recipient_name", "")
        notes = serializer.validated_data.get("notes", "")

        completed_delivery = complete_delivery_service(
            delivery_id=delivery.id,
            recipient_name=recipient_name,
            notes=notes,
            user=request.user,
        )

        return Response(DeliverySerializer(completed_delivery).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="mark-not-delivered")
    def mark_not_delivered(self, request, pk=None):
        """
        Action to mark a delivery as not delivered with a required reason.
        """
        delivery = self.get_object()
        from .serializers import NotDeliveredInputSerializer
        serializer = NotDeliveredInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        failed_reason = serializer.validated_data["failed_reason"]
        notes = serializer.validated_data.get("notes", "")

        from .services import mark_delivery_not_delivered_service
        updated_delivery = mark_delivery_not_delivered_service(
            delivery_id=delivery.id,
            failed_reason=failed_reason,
            notes=notes,
            user=request.user,
        )
        return Response(DeliverySerializer(updated_delivery).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="assign-driver", permission_classes=[permissions.IsAuthenticated, IsAssignedDriverOrManagerOwner])
    def assign_driver(self, request, pk=None):
        """
        Action for Manager/Owner to assign or reassign a delivery to a driver.
        Enforces route compatibility check unless allow_cross_route=True.
        """
        if request.user.role not in ["OWNER", "MANAGER"] and not request.user.is_superuser:
            return Response({"detail": "Only Managers and Owners can assign drivers."}, status=status.HTTP_403_FORBIDDEN)

        delivery = self.get_object()
        from .serializers import AssignDriverSerializer
        serializer = AssignDriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver_id = serializer.validated_data["driver_id"]
        allow_cross_route = serializer.validated_data.get("allow_cross_route", False)
        notes = serializer.validated_data.get("notes", "")

        from .services import assign_delivery_driver_service
        try:
            updated_delivery = assign_delivery_driver_service(
                delivery_id=delivery.id,
                driver_id=driver_id,
                allow_cross_route=allow_cross_route,
                notes=notes,
                user=request.user,
            )
            return Response(DeliverySerializer(updated_delivery).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

