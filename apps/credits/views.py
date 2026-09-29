from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.permissions import IsManagerOrOwner
from .models import CreditTransaction
from .serializers import CreditTransactionSerializer, AdjustmentCreateSerializer

class CreditTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ledger of credit history for all customer shops.
    - Owner & Manager: View full ledger across all customers and routes.
    - Driver: Isolated strictly to ledger entries for customers on their route.
    """
    serializer_class = CreditTransactionSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["customer__name", "notes", "reference_order__order_number", "reference_payment__payment_number"]
    ordering_fields = ["created_at", "amount", "balance_after"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return CreditTransaction.objects.none()

        queryset = CreditTransaction.objects.select_related(
            "customer",
            "customer__route",
            "reference_order",
            "reference_payment",
            "recorded_by",
        )

        customer_id = self.request.query_params.get("customer")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        tx_type = self.request.query_params.get("type")
        if tx_type:
            queryset = queryset.filter(transaction_type=tx_type)

        if user.is_superuser or user.role in ["OWNER", "MANAGER"]:
            return queryset.order_by("-created_at")

        # Driver isolation: only ledger entries for shops on driver's assigned route
        if user.role == "DRIVER":
            if hasattr(user, "driver_profile") and user.driver_profile and user.driver_profile.assigned_route:
                return queryset.filter(customer__route=user.driver_profile.assigned_route).order_by("-created_at")
            return CreditTransaction.objects.none()

        return CreditTransaction.objects.none()

    @action(detail=False, methods=["post"], permission_classes=[IsManagerOrOwner], url_path="adjust")
    def create_adjustment(self, request):
        """
        Endpoint for Owner or Manager to record an authorized credit ledger adjustment.
        """
        serializer = AdjustmentCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        tx = serializer.save()
        return Response(CreditTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)
