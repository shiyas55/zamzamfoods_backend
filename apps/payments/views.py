import datetime
from decimal import Decimal
from django.db import models, transaction
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

    @action(detail=False, methods=["post"], url_path="sync-daily-payment", permission_classes=[IsManagerOrOwner])
    def sync_daily_payment(self, request):
        """
        Synchronizes daily customer payments (Cash & GPay) from wholesale daily entry.
        Replaces/adjusts existing payments so the total matches exactly what was entered,
        rather than accumulating duplicate payments on every submit or reload.
        """
        customer_id = request.data.get("customer_id")
        date_str = request.data.get("date")
        cash_raw = request.data.get("cash_amount")
        gpay_raw = request.data.get("gpay_amount")
        order_id = request.data.get("order_id")

        if not customer_id or not date_str:
            return Response({"error": "customer_id and date are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        target_cash = Decimal(str(cash_raw or "0.00")).quantize(Decimal("0.01"))
        target_gpay = Decimal(str(gpay_raw or "0.00")).quantize(Decimal("0.01"))

        if target_cash < Decimal("0.00") or target_gpay < Decimal("0.00"):
            return Response({"error": "Payment amounts cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.customers.models import Customer
        from apps.orders.models import Order
        from apps.credits.models import CreditTransaction
        from apps.payments.services import record_payment_service

        with transaction.atomic():
            try:
                customer = Customer.objects.select_for_update().get(id=customer_id)
            except Customer.DoesNotExist:
                return Response({"error": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

            order = Order.objects.filter(id=order_id).first() if order_id else None
            payment_time = timezone.make_aware(datetime.datetime.combine(target_date, datetime.time(12, 0)))

            results = {}
            for method, target_amt in [(Payment.Method.CASH, target_cash), (Payment.Method.GPAY_UPI, target_gpay)]:
                existing_pays = list(Payment.objects.filter(
                    customer=customer,
                    received_at__date=target_date,
                    payment_method=method,
                    status=Payment.Status.COMPLETED
                ).order_by("created_at"))

                current_sum = sum((p.amount for p in existing_pays), Decimal("0.00"))
                diff = target_amt - current_sum

                if diff == Decimal("0.00") and len(existing_pays) <= 1:
                    results[method] = str(target_amt)
                    continue

                if target_amt == Decimal("0.00"):
                    # User cleared payment to 0
                    for p in existing_pays:
                        CreditTransaction.objects.filter(reference_payment=p).delete()
                        p.delete()
                    customer.current_balance = (customer.current_balance + current_sum).quantize(Decimal("0.01"))
                    customer.save(update_fields=["current_balance", "updated_at"])
                    results[method] = "0.00"
                elif not existing_pays:
                    # Brand new payment
                    p = record_payment_service(
                        customer_id=customer.id,
                        amount=target_amt,
                        payment_method=method,
                        collected_by=request.user,
                        order_id=order.id if order else None,
                        notes=f"Wholesale counter {method} collection ({date_str})",
                        received_at=payment_time,
                    )
                    CreditTransaction.objects.filter(reference_payment=p).update(created_at=payment_time)
                    results[method] = str(target_amt)
                else:
                    # Payment was edited: adjust primary payment and delete any extra duplicates
                    primary_pay = existing_pays[0]
                    primary_pay.amount = target_amt
                    if order and not primary_pay.order_id:
                        primary_pay.order = order
                    primary_pay.received_at = payment_time
                    primary_pay.save(update_fields=["amount", "order", "received_at", "updated_at"])

                    for extra_p in existing_pays[1:]:
                        CreditTransaction.objects.filter(reference_payment=extra_p).delete()
                        extra_p.delete()

                    # Balance adjustment: more paid (diff > 0) reduces balance, less paid (diff < 0) increases balance
                    customer.current_balance = (customer.current_balance - diff).quantize(Decimal("0.01"))
                    customer.save(update_fields=["current_balance", "updated_at"])

                    ledger_tx = CreditTransaction.objects.filter(reference_payment=primary_pay).first()
                    if ledger_tx:
                        ledger_tx.amount = -target_amt
                        ledger_tx.balance_after = customer.current_balance
                        ledger_tx.created_at = payment_time
                        ledger_tx.save(update_fields=["amount", "balance_after", "created_at", "updated_at"])
                    else:
                        tx_type = (
                            CreditTransaction.TransactionType.CASH_PAYMENT
                            if method == Payment.Method.CASH
                            else CreditTransaction.TransactionType.GPAY_PAYMENT
                        )
                        CreditTransaction.objects.create(
                            customer=customer,
                            transaction_type=tx_type,
                            amount=-target_amt,
                            balance_after=customer.current_balance,
                            reference_payment=primary_pay,
                            reference_order=order,
                            notes=f"Adjusted wholesale counter {method} collection ({date_str})",
                            recorded_by=request.user,
                            created_at=payment_time,
                        )
                    results[method] = str(target_amt)

            return Response({
                "status": "success",
                "customer_id": str(customer.id),
                "customer_name": customer.name,
                "current_balance": str(customer.current_balance),
                "date": date_str,
                "cash_amount": results.get(Payment.Method.CASH, str(target_cash)),
                "gpay_amount": results.get(Payment.Method.GPAY_UPI, str(target_gpay)),
            }, status=status.HTTP_200_OK)
