from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from apps.common.permissions import IsManagerOrOwner, IsAssignedDriverOrManagerOwner
from .models import Order
from .serializers import OrderSerializer, CreateOrderSerializer, UpdateOrderSerializer

class OrderViewSet(viewsets.ModelViewSet):
    """
    CRUD for sales orders.
    - Owner & Manager: Full access across all routes and drivers.
    - Driver: Isolated strictly to orders assigned to their user/route.
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["order_number", "customer__name", "customer__phone"]
    ordering_fields = ["order_date", "total_amount", "created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateOrderSerializer
        if self.action in ["update", "partial_update"]:
            return UpdateOrderSerializer
        return OrderSerializer

    def get_permissions(self):
        if self.action in ["create", "destroy", "update", "partial_update"]:
            return [IsManagerOrOwner()]
        return [permissions.IsAuthenticated(), IsAssignedDriverOrManagerOwner()]


    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()

        queryset = Order.objects.select_related("customer", "route", "driver", "driver__user").prefetch_related("items__product")

        # Query filters for managers/owners
        route_id = self.request.query_params.get("route")
        if route_id:
            queryset = queryset.filter(route_id=route_id)

        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        date_param = self.request.query_params.get("date")
        if date_param:
            queryset = queryset.filter(order_date=date_param)

        customer_id = self.request.query_params.get("customer")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        if user.is_superuser or user.role in ["OWNER", "MANAGER"]:
            return queryset.order_by("-order_date", "-created_at").distinct()

        # Driver data isolation: driver ONLY sees their assigned orders
        if user.role == "DRIVER":
            return queryset.filter(driver__user=user).order_by("-order_date", "-created_at").distinct()

        return Order.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        output_serializer = OrderSerializer(order)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        output_serializer = OrderSerializer(order)
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status in [Order.Status.LOCKED, Order.Status.BILLING, Order.Status.DELIVERY_CREATED, Order.Status.COMPLETED]:
            raise PermissionDenied(f"Cannot delete order because its status is {instance.get_status_display()}.")
        return super().destroy(request, *args, **kwargs)
        
    @action(detail=True, methods=["post"], permission_classes=[IsManagerOrOwner])
    def reopen(self, request, pk=None):
        instance = self.get_object()
        reason = request.data.get("reason")
        if not reason:
            return Response({"error": "A reason is required to reopen an order."}, status=status.HTTP_400_BAD_REQUEST)
            
        from .services import reopen_order_service
        try:
            order = reopen_order_service(instance.id, request.user, reason)
            return Response(OrderSerializer(order).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(detail=True, methods=["get"], permission_classes=[IsManagerOrOwner])
    def activity(self, request, pk=None):
        instance = self.get_object()
        logs = instance.activity_logs.all()
        data = []
        for log in logs:
            data.append({
                "id": str(log.id),
                "timestamp": log.created_at,
                "action": log.action,
                "user_name": log.user_name,
                "user_role": log.user_role,
                "source": log.source,
                "details": log.details,
            })
        return Response(data)

