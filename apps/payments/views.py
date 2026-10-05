from decimal import Decimal
from django.db import models
from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.permissions import IsManagerOrOwner
from .models import Payment
from .serializers import PaymentSerializer, CreatePaymentSerializer

class PaymentViewSet(viewsets.ModelViewSet):
    """
    Endpoints for logging and auditing customer payments.
    - Owner & Manager: View all payments, access financial summaries.
    - Driver: View only their own collected payments; record collections on delivery.
    """
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["payment_number", "customer__name", "reference_number"]
    ordering_fields = ["received_at", "amount"]

    def get_serializer_class(self):
        if self.action == "create":
            return CreatePaymentSerializer
        return PaymentSerializer

    def get_permissions(self):
        if self.action in ["destroy", "update", "partial_update"]:
            # Financial records cannot be casually edited or deleted
            return [IsManagerOrOwner()]
        return [permissions.IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        """
        Direct hard-deletion of financial records is strictly prohibited.
        """
        return Response(
            {"error": "Direct deletion of financial records is prohibited to protect financial auditability. Use payment reversal with an authorized audit reason."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def update(self, request, *args, **kwargs):
        """Financial payment records are immutable once committed."""
        return Response(
            {"error": "Financial payment records are immutable once committed. Use payment reversal with an authorized audit reason."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        """Financial payment records are immutable once committed."""
        return Response(
            {"error": "Financial payment records are immutable once committed. Use payment reversal with an authorized audit reason."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Payment.objects.none()

        queryset = Payment.objects.select_related("customer", "customer__route", "collected_by", "staff_member", "order", "reversed_by")

        # Query filters
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        route_id = self.request.query_params.get("route")
        if route_id:
            queryset = queryset.filter(customer__route_id=route_id)

        driver_id = self.request.query_params.get("driver") or self.request.query_params.get("collector")
        if driver_id:
            queryset = queryset.filter(
                models.Q(collected_by_id=driver_id)
                | models.Q(staff_member_id=driver_id)
                | models.Q(staff_member__user_id=driver_id)
            )

        staff_member_id = self.request.query_params.get("staff_member")
        if staff_member_id:
            queryset = queryset.filter(
                models.Q(staff_member_id=staff_member_id)
                | models.Q(staff_member__user_id=staff_member_id)
                | models.Q(collected_by_id=staff_member_id)
            )

        method = self.request.query_params.get("method")
        if method:
            queryset = queryset.filter(payment_method=method)

        payment_status = self.request.query_params.get("status")
        if payment_status:
            queryset = queryset.filter(status=payment_status)

        date_param = self.request.query_params.get("date")
        if date_param:
            queryset = queryset.filter(received_at__date=date_param)

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date and end_date:
            queryset = queryset.filter(received_at__date__gte=start_date, received_at__date__lte=end_date)

        payment_type = self.request.query_params.get("payment_type")
        if payment_type == "ORDER_PAYMENT":
            queryset = queryset.filter(order__isnull=False)
        elif payment_type == "PREVIOUS_CREDIT":
            queryset = queryset.filter(order__isnull=True)

        if user.is_superuser or user.role in ["OWNER", "MANAGER"]:
            return queryset.order_by("-received_at")

        # Driver isolation: only payments collected by this driver
        if user.role == "DRIVER":
            return queryset.filter(collected_by=user).order_by("-received_at")

        return Payment.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="reverse", permission_classes=[IsManagerOrOwner])
    def reverse_payment(self, request, pk=None):
        """
        Safely reverses/voids a payment, restoring customer debt and posting to credit ledger.
        Requires an audit explanation reason.
        """
        from .serializers import ReversePaymentSerializer
        from .services import reverse_payment_service

        serializer = ReversePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        payment = self.get_object()
        try:
            reversed_payment = reverse_payment_service(
                payment_id=payment.id,
                user=request.user,
                reason=serializer.validated_data["reason"],
            )
            return Response(PaymentSerializer(reversed_payment).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"], url_path="daily_summary", permission_classes=[permissions.IsAuthenticated])
    def daily_summary(self, request):
        """
        Calculates today's cash vs UPI collections.
        Filtered by driver if caller is a driver; system-wide if manager/owner.
        """
        today = timezone.localdate()
        date_str = request.query_params.get("date")
        if date_str:
            try:
                today = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        qs = self.get_queryset().filter(received_at__date=today, status=Payment.Status.COMPLETED)

        cash_total = qs.filter(payment_method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        upi_total = qs.filter(payment_method=Payment.Method.GPAY_UPI).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        total_collected = cash_total + upi_total

        return Response({
            "date": today,
            "total_collected": total_collected,
            "cash_total": cash_total,
            "upi_total": upi_total,
            "count": qs.count(),
        })

    @action(detail=False, methods=["get"], url_path="daily-summary", permission_classes=[permissions.IsAuthenticated])
    def daily_summary_kebab(self, request):
        return self.daily_summary(request)
