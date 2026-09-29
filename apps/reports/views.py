import datetime
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers as drf_serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from apps.common.permissions import IsManagerOrOwner
from apps.customers.models import Customer
from apps.routes.models import Route, Driver, DriverExpense
from apps.orders.models import Order
from apps.deliveries.models import Delivery
from apps.payments.models import Payment
from apps.products.models import Product


def resolve_date_range(request):
    """
    Parses preset or custom date range:
    - preset: 'today', 'yesterday', 'this_week', 'this_month'
    - custom: start_date, end_date (YYYY-MM-DD)
    Returns: (start_date: date, end_date: date, preset_name: str)
    """
    today = timezone.localdate()
    preset = request.query_params.get("date_preset", "today").lower()
    start_date_param = request.query_params.get("start_date")
    end_date_param = request.query_params.get("end_date")

    if start_date_param and end_date_param:
        try:
            start_date = datetime.datetime.strptime(start_date_param, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(end_date_param, "%Y-%m-%d").date()
            return start_date, end_date, "custom"
        except (ValueError, TypeError):
            pass

    if preset == "yesterday":
        yest = today - datetime.timedelta(days=1)
        return yest, yest, "yesterday"
    elif preset == "this_week":
        start_week = today - datetime.timedelta(days=today.weekday())
        return start_week, today, "this_week"
    elif preset == "this_month":
        start_month = today.replace(day=1)
        return start_month, today, "this_month"
    else:  # default 'today'
        return today, today, "today"


class DashboardSummaryView(APIView):
    """
    Role-aware centralized dashboard summary endpoint with full date filtering.
    Supports Today, Yesterday, This Week, This Month, and Custom Date Range.
    Provides verified metrics: Sales, Collections, Credit, Deliveries, Expenses, Net Collection.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: drf_serializers.DictField()})
    def get(self, request):
        user = request.user
        start_date, end_date, preset_name = resolve_date_range(request)

        # DRIVER DASHBOARD (Mobile-first metrics for assigned route)
        if user.role == "DRIVER":
            driver = getattr(user, "driver_profile", None)
            if not driver:
                return Response({
                    "role": "DRIVER",
                    "error": "No driver profile attached.",
                }, status=status.HTTP_404_NOT_FOUND)

            route = driver.assigned_route
            deliveries_qs = Delivery.objects.filter(
                driver=driver,
                order__order_date__gte=start_date,
                order__order_date__lte=end_date,
            )
            total_deliveries = deliveries_qs.count()
            completed_deliveries = deliveries_qs.filter(status=Delivery.Status.DELIVERED).count()
            not_delivered_count = deliveries_qs.filter(
                status__in=[Delivery.Status.NOT_DELIVERED, Delivery.Status.FAILED]
            ).count()
            pending_deliveries = deliveries_qs.filter(
                status__in=[Delivery.Status.ASSIGNED, Delivery.Status.IN_TRANSIT]
            ).count()

            # Collections in date range
            payments_qs = Payment.objects.filter(
                collected_by=user,
                received_at__date__gte=start_date,
                received_at__date__lte=end_date,
                status=Payment.Status.COMPLETED
            )
            cash_collected = payments_qs.filter(payment_method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            upi_collected = payments_qs.filter(payment_method=Payment.Method.GPAY_UPI).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            total_collected = cash_collected + upi_collected

            # Driver expenses in date range
            expenses_qs = DriverExpense.objects.filter(
                driver=driver,
                date__gte=start_date,
                date__lte=end_date,
            )
            total_expenses = expenses_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            net_collection = total_collected - total_expenses

            return Response({
                "role": "DRIVER",
                "date": str(start_date) if start_date == end_date else f"{start_date} to {end_date}",
                "start_date": str(start_date),
                "end_date": str(end_date),
                "date_preset": preset_name,
                "driver_name": user.get_full_name() or user.username,
                "route_name": route.name if route else "Unassigned",
                "route_id": str(route.id) if route else None,
                "vehicle_number": driver.vehicle_number,
                "total_deliveries": total_deliveries,
                "completed_deliveries": completed_deliveries,
                "not_delivered_count": not_delivered_count,
                "pending_deliveries": pending_deliveries,
                "cash_collected": cash_collected,
                "upi_collected": upi_collected,
                "total_collected": total_collected,
                "today_expenses": total_expenses,
                "net_collection": net_collection,
            })

        # OWNER & MANAGER DASHBOARD
        orders_qs = Order.objects.filter(order_date__gte=start_date, order_date__lte=end_date)
        active_orders_qs = orders_qs.exclude(status=Order.Status.CANCELLED)
        period_sales = active_orders_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        period_orders_count = active_orders_qs.count()

        # Deliveries
        deliveries_qs = Delivery.objects.filter(order__order_date__gte=start_date, order__order_date__lte=end_date)
        total_deliveries = deliveries_qs.count()
        completed_deliveries = deliveries_qs.filter(status=Delivery.Status.DELIVERED).count()
        not_delivered_count = deliveries_qs.filter(status__in=[Delivery.Status.NOT_DELIVERED, Delivery.Status.FAILED]).count()
        pending_deliveries = deliveries_qs.filter(status__in=[Delivery.Status.ASSIGNED, Delivery.Status.IN_TRANSIT]).count()

        # Collections
        payments_qs = Payment.objects.filter(
            received_at__date__gte=start_date,
            received_at__date__lte=end_date,
            status=Payment.Status.COMPLETED,
        )
        cash_collected = payments_qs.filter(payment_method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        upi_collected = payments_qs.filter(payment_method=Payment.Method.GPAY_UPI).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        total_collected = cash_collected + upi_collected

        # Driver Expenses
        expenses_qs = DriverExpense.objects.filter(date__gte=start_date, date__lte=end_date)
        period_expenses = expenses_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Net Collection = Collection - Driver Expenses
        net_collection = total_collected - period_expenses

        # Period Credit = Sales - Collections (Net Credit Extended)
        period_credit = max(Decimal("0.00"), period_sales - total_collected)

        # Receivables & Customers
        active_customers = Customer.objects.filter(is_active=True)
        total_customers = active_customers.count()
        total_receivable = active_customers.aggregate(total=Sum("current_balance"))["total"] or Decimal("0.00")
        credit_exceeded_count = active_customers.filter(current_balance__gt=Decimal("5000.00")).count()

        # Route Breakdown in Date Range
        routes = Route.objects.filter(is_active=True)
        route_stats = []
        for r in routes:
            r_orders = orders_qs.filter(route=r).exclude(status=Order.Status.CANCELLED)
            r_sales = r_orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
            r_payments = payments_qs.filter(customer__route=r).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            r_expenses = expenses_qs.filter(driver__assigned_route=r).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            r_receivables = active_customers.filter(route=r).aggregate(total=Sum("current_balance"))["total"] or Decimal("0.00")
            r_deliv = deliveries_qs.filter(route=r)

            route_stats.append({
                "route_id": str(r.id),
                "route_name": r.name,
                "route_code": r.code,
                "shops_count": active_customers.filter(route=r).count(),
                "today_orders_count": r_orders.count(),
                "today_sales": r_sales,
                "total_deliveries": r_deliv.count(),
                "completed_deliveries": r_deliv.filter(status=Delivery.Status.DELIVERED).count(),
                "not_delivered_count": r_deliv.filter(status__in=[Delivery.Status.NOT_DELIVERED, Delivery.Status.FAILED]).count(),
                "today_collected": r_payments,
                "today_expenses": r_expenses,
                "net_collected": r_payments - r_expenses,
                "total_receivable": r_receivables,
            })

        data = {
            "role": user.role,
            "date": str(start_date) if start_date == end_date else f"{start_date} to {end_date}",
            "start_date": str(start_date),
            "end_date": str(end_date),
            "date_preset": preset_name,
            "today_orders_count": period_orders_count,
            "today_sales": period_sales,
            "total_deliveries": total_deliveries,
            "completed_deliveries": completed_deliveries,
            "not_delivered_count": not_delivered_count,
            "pending_deliveries": pending_deliveries,
            "cash_collected": cash_collected,
            "upi_collected": upi_collected,
            "total_collected": total_collected,
            "today_expenses": period_expenses,
            "today_credit": period_credit,
            "net_collection": net_collection,
            "total_customers": total_customers,
            "total_receivable": total_receivable,
            "credit_exceeded_count": credit_exceeded_count,
            "route_breakdown": route_stats,
        }

        return Response(data)


class DriverPerformanceReportView(APIView):
    """
    Factual operational performance report for delivery drivers.
    Shows assigned deliveries, delivered, not delivered, pending, collections, expenses, and net collection.
    Filterable by Date (Preset or Custom Range), Driver ID, and Route ID.
    Strictly restricted to Owner and Manager.
    """
    permission_classes = [permissions.IsAuthenticated, IsManagerOrOwner]

    @extend_schema(responses={200: drf_serializers.ListField()})
    def get(self, request):
        start_date, end_date, preset_name = resolve_date_range(request)

        drivers = Driver.objects.filter(is_active=True).select_related("user", "assigned_route")

        # Filters
        driver_id = request.query_params.get("driver")
        if driver_id:
            drivers = drivers.filter(id=driver_id)

        route_id = request.query_params.get("route")
        if route_id:
            drivers = drivers.filter(assigned_route_id=route_id)

        results = []
        for d in drivers:
            # Deliveries in range
            deliv_qs = Delivery.objects.filter(
                driver=d,
                order__order_date__gte=start_date,
                order__order_date__lte=end_date,
            )
            total_assigned = deliv_qs.count()
            delivered = deliv_qs.filter(status=Delivery.Status.DELIVERED).count()
            not_delivered = deliv_qs.filter(status__in=[Delivery.Status.NOT_DELIVERED, Delivery.Status.FAILED]).count()
            pending = deliv_qs.filter(status__in=[Delivery.Status.ASSIGNED, Delivery.Status.IN_TRANSIT]).count()

            # Collections in range
            pay_qs = Payment.objects.filter(
                collected_by=d.user,
                received_at__date__gte=start_date,
                received_at__date__lte=end_date,
                status=Payment.Status.COMPLETED,
            )
            cash = pay_qs.filter(payment_method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            upi = pay_qs.filter(payment_method=Payment.Method.GPAY_UPI).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            total_collected = cash + upi

            # Expenses in range
            exp_qs = DriverExpense.objects.filter(
                driver=d,
                date__gte=start_date,
                date__lte=end_date,
            )
            total_expenses = exp_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

            net_collection = total_collected - total_expenses

            results.append({
                "driver_id": str(d.id),
                "driver_name": d.user.get_full_name() or d.user.username,
                "phone_number": d.phone_number,
                "vehicle_number": d.vehicle_number,
                "route_id": str(d.assigned_route.id) if d.assigned_route else None,
                "route_name": d.assigned_route.name if d.assigned_route else "Unassigned",
                "route_code": d.assigned_route.code if d.assigned_route else "",
                "total_assigned": total_assigned,
                "delivered": delivered,
                "not_delivered": not_delivered,
                "pending": pending,
                "cash_collected": cash,
                "upi_collected": upi,
                "collection_amount": total_collected,
                "expenses": total_expenses,
                "net_collection": net_collection,
            })

        return Response({
            "start_date": str(start_date),
            "end_date": str(end_date),
            "date_preset": preset_name,
            "drivers": results,
        })


class DriverDetailReportView(APIView):
    """
    Detailed operational drilldown for a single driver:
    - Assigned deliveries with customer & order details
    - Collections list with payment methods & receipts
    - Expenses list with categories & notes
    - Factual totals
    Permissions:
    - Driver can ONLY access their own driver ID.
    - Owner and Manager have full access.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: drf_serializers.DictField()})
    def get(self, request, driver_id):
        user = request.user
        try:
            driver = Driver.objects.select_related("user", "assigned_route").get(id=driver_id)
        except (Driver.DoesNotExist, ValueError):
            return Response({"error": "Driver not found."}, status=status.HTTP_404_NOT_FOUND)

        # Strict driver data isolation: driver cannot view another driver's detail
        if user.role == "DRIVER" and driver.user != user:
            return Response({"error": "Access denied to other driver records."}, status=status.HTTP_403_FORBIDDEN)

        start_date, end_date, preset_name = resolve_date_range(request)

        # Deliveries
        deliv_qs = Delivery.objects.filter(
            driver=driver,
            order__order_date__gte=start_date,
            order__order_date__lte=end_date,
        ).select_related("order", "order__customer", "order__route").order_by("-created_at")

        deliveries_list = [
            {
                "id": str(dl.id),
                "delivery_number": dl.delivery_number,
                "order_number": dl.order.order_number,
                "customer_name": dl.order.customer.name,
                "customer_address": dl.order.customer.address,
                "total_amount": dl.order.total_amount,
                "status": dl.status,
                "failed_reason": dl.failed_reason,
                "date": dl.order.order_date,
            }
            for dl in deliv_qs
        ]

        # Collections
        pay_qs = Payment.objects.filter(
            collected_by=driver.user,
            received_at__date__gte=start_date,
            received_at__date__lte=end_date,
            status=Payment.Status.COMPLETED,
        ).select_related("customer").order_by("-received_at")

        collections_list = [
            {
                "id": str(p.id),
                "payment_number": p.payment_number,
                "customer_name": p.customer.name,
                "amount": p.amount,
                "payment_method": p.payment_method,
                "date": p.received_at,
            }
            for p in pay_qs
        ]

        # Expenses
        exp_qs = DriverExpense.objects.filter(
            driver=driver,
            date__gte=start_date,
            date__lte=end_date,
        ).order_by("-date", "-created_at")

        expenses_list = [
            {
                "id": str(e.id),
                "category": e.category,
                "category_display": e.get_category_display(),
                "amount": e.amount,
                "date": e.date,
                "notes": e.notes,
            }
            for e in exp_qs
        ]

        # Summary calculations
        total_assigned = len(deliveries_list)
        delivered_count = sum(1 for d in deliveries_list if d["status"] == Delivery.Status.DELIVERED)
        not_delivered_count = sum(1 for d in deliveries_list if d["status"] in [Delivery.Status.NOT_DELIVERED, Delivery.Status.FAILED])
        pending_count = total_assigned - delivered_count - not_delivered_count

        total_collected = sum(Decimal(str(p["amount"])) for p in collections_list)
        total_expenses = sum(Decimal(str(e["amount"])) for e in expenses_list)
        net_collection = total_collected - total_expenses

        return Response({
            "driver_id": str(driver.id),
            "driver_name": driver.user.get_full_name() or driver.user.username,
            "vehicle_number": driver.vehicle_number,
            "route_name": driver.assigned_route.name if driver.assigned_route else "Unassigned",
            "start_date": str(start_date),
            "end_date": str(end_date),
            "date_preset": preset_name,
            "summary": {
                "assigned": total_assigned,
                "delivered": delivered_count,
                "not_delivered": not_delivered_count,
                "pending": pending_count,
                "total_collection": total_collected,
                "total_expenses": total_expenses,
                "net_collection": net_collection,
            },
            "deliveries": deliveries_list,
            "collections": collections_list,
            "expenses": expenses_list,
        })


class OutstandingCreditReportView(APIView):
    """
    Outstanding credit ledger summary (receivables report) for Owner and Manager.
    Enhanced with last payment, last order, and age of outstanding amount.
    """
    permission_classes = [IsManagerOrOwner]

    @extend_schema(responses={200: drf_serializers.DictField()})
    def get(self, request):
        today = timezone.localdate()
        route_id = request.query_params.get("route")
        aging_filter = request.query_params.get("aging_bucket")
        search_query = request.query_params.get("search", "").strip()

        customers = Customer.objects.filter(is_active=True, current_balance__gt=Decimal("0.00"))
        if route_id:
            customers = customers.filter(route_id=route_id)

        if search_query:
            customers = customers.filter(
                Q(name__icontains=search_query) | Q(owner_name__icontains=search_query) | Q(phone__icontains=search_query)
            )

        customers = customers.select_related("route").order_by("-current_balance")

        results = []
        bucket_counts = {
            "0_to_7_days": Decimal("0.00"),
            "8_to_15_days": Decimal("0.00"),
            "16_to_30_days": Decimal("0.00"),
            "30_plus_days": Decimal("0.00"),
        }

        for c in customers:
            last_p = c.payments.filter(status=Payment.Status.COMPLETED).order_by("-received_at").first()
            last_payment_info = None
            if last_p:
                last_payment_info = {
                    "payment_number": last_p.payment_number,
                    "date": str(last_p.received_at.date()),
                    "amount": str(last_p.amount),
                    "method": last_p.payment_method,
                }

            last_o = c.orders.exclude(status=Order.Status.CANCELLED).order_by("-order_date").first()
            last_order_info = None
            if last_o:
                last_order_info = {
                    "order_number": last_o.order_number,
                    "date": str(last_o.order_date),
                    "amount": str(last_o.total_amount),
                }

            if last_p:
                days_outstanding = (today - last_p.received_at.date()).days
            elif last_o:
                days_outstanding = (today - last_o.order_date).days
            else:
                days_outstanding = (today - c.created_at.date()).days

            days_outstanding = max(0, days_outstanding)

            if days_outstanding <= 7:
                bucket = "0-7 days"
                bucket_key = "0_to_7_days"
            elif days_outstanding <= 15:
                bucket = "8-15 days"
                bucket_key = "8_to_15_days"
            elif days_outstanding <= 30:
                bucket = "16-30 days"
                bucket_key = "16_to_30_days"
            else:
                bucket = "30+ days"
                bucket_key = "30_plus_days"

            bucket_counts[bucket_key] += c.current_balance

            if aging_filter and bucket != aging_filter:
                continue

            results.append({
                "customer_id": str(c.id),
                "customer_name": c.name,
                "owner_name": c.owner_name,
                "phone": c.phone,
                "route_name": c.route.name if c.route else "Unassigned",
                "current_balance": c.current_balance,
                "credit_limit": c.credit_limit,
                "is_exceeded": c.is_credit_exceeded,
                "last_payment": last_payment_info,
                "last_order": last_order_info,
                "days_outstanding": days_outstanding,
                "aging_bucket": bucket,
            })

        total_outstanding = sum(item["current_balance"] for item in results) if results else Decimal("0.00")

        return Response({
            "total_outstanding": total_outstanding,
            "customer_count": len(results),
            "aging_summary": bucket_counts,
            "customers": results,
        })


class CollectionReportView(APIView):
    """
    Collection Report for Owner, Manager, and Drivers.
    Filters: Date range, Driver, Route, Customer, Payment Method, Status, Allocation.
    Displays: Cash, UPI, Previous credit collection, Today's order collection, Total, Reversals.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: drf_serializers.DictField()})
    def get(self, request):
        user = request.user
        start_date, end_date, preset_name = resolve_date_range(request)

        qs = Payment.objects.select_related("customer", "customer__route", "collected_by", "order", "reversed_by")

        # Driver isolation
        if user.role == "DRIVER":
            qs = qs.filter(collected_by=user)
        else:
            driver_param = request.query_params.get("driver")
            if driver_param:
                qs = qs.filter(Q(collected_by_id=driver_param) | Q(collected_by__driver_profile__id=driver_param))

        # Date filter
        qs = qs.filter(received_at__date__gte=start_date, received_at__date__lte=end_date)

        # Route filter
        route_param = request.query_params.get("route")
        if route_param:
            qs = qs.filter(customer__route_id=route_param)

        # Customer filter
        customer_param = request.query_params.get("customer")
        if customer_param:
            qs = qs.filter(customer_id=customer_param)

        # Method filter
        method_param = request.query_params.get("method")
        if method_param:
            qs = qs.filter(payment_method=method_param)

        # Status filter
        status_param = request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        # Payment type filter
        type_param = request.query_params.get("payment_type")
        if type_param == "ORDER_PAYMENT":
            qs = qs.filter(order__isnull=False)
        elif type_param == "PREVIOUS_CREDIT":
            qs = qs.filter(order__isnull=True)

        # Summary calculations for COMPLETED payments
        completed_qs = qs.filter(status=Payment.Status.COMPLETED)
        cash_total = completed_qs.filter(payment_method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        upi_total = completed_qs.filter(payment_method=Payment.Method.GPAY_UPI).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        total_collected = cash_total + upi_total

        today_order_collected = completed_qs.filter(order__isnull=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        previous_credit_collected = completed_qs.filter(order__isnull=True).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Reversals
        reversed_qs = qs.filter(status=Payment.Status.REVERSED)
        reversed_amount = reversed_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        collections_list = [
            {
                "id": str(p.id),
                "payment_number": p.payment_number,
                "customer_id": str(p.customer_id),
                "customer_name": p.customer.name,
                "customer_phone": p.customer.phone,
                "route_name": p.customer.route.name if p.customer.route else "Unassigned",
                "route_id": str(p.customer.route_id) if p.customer.route_id else None,
                "driver_name": p.collected_by.get_full_name() or p.collected_by.username if p.collected_by else "Staff",
                "amount": p.amount,
                "payment_method": p.payment_method,
                "payment_type": "ORDER_PAYMENT" if p.order_id else "PREVIOUS_CREDIT",
                "order_number": p.order.order_number if p.order else None,
                "status": p.status,
                "reference_number": p.reference_number,
                "notes": p.notes,
                "received_at": p.received_at,
                "reversed_at": p.reversed_at,
                "reversal_reason": p.reversal_reason,
                "reversed_by_name": p.reversed_by.get_full_name() or p.reversed_by.username if p.reversed_by else None,
            }
            for p in qs.order_by("-received_at")
        ]

        return Response({
            "start_date": str(start_date),
            "end_date": str(end_date),
            "date_preset": preset_name,
            "summary": {
                "total_collected": total_collected,
                "cash_total": cash_total,
                "upi_total": upi_total,
                "today_order_collected": today_order_collected,
                "previous_credit_collected": previous_credit_collected,
                "completed_count": completed_qs.count(),
                "reversed_count": reversed_qs.count(),
                "reversed_amount": reversed_amount,
            },
            "collections": collections_list,
        })


class DriverCollectionReportView(APIView):
    """
    Operational financial report of driver collections:
    Driver, Route, Orders delivered, Cash, UPI, Orders Collection, Previous Credit Collection, Total Collection, Expenses, Net Collection.
    Not a performance ranking; operational financial reconciliation report.
    """
    permission_classes = [permissions.IsAuthenticated, IsManagerOrOwner]

    @extend_schema(responses={200: drf_serializers.DictField()})
    def get(self, request):
        start_date, end_date, preset_name = resolve_date_range(request)

        drivers = Driver.objects.filter(is_active=True).select_related("user", "assigned_route")

        driver_id = request.query_params.get("driver")
        if driver_id:
            drivers = drivers.filter(id=driver_id)

        route_id = request.query_params.get("route")
        if route_id:
            drivers = drivers.filter(assigned_route_id=route_id)

        results = []
        grand_total_collected = Decimal("0.00")
        grand_total_expenses = Decimal("0.00")
        grand_net_collected = Decimal("0.00")

        for d in drivers:
            # Deliveries delivered
            deliv_qs = Delivery.objects.filter(
                driver=d,
                order__order_date__gte=start_date,
                order__order_date__lte=end_date,
                status=Delivery.Status.DELIVERED,
            )
            orders_delivered = deliv_qs.count()

            # Collections
            pay_qs = Payment.objects.filter(
                collected_by=d.user,
                received_at__date__gte=start_date,
                received_at__date__lte=end_date,
                status=Payment.Status.COMPLETED,
            )
            cash = pay_qs.filter(payment_method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            upi = pay_qs.filter(payment_method=Payment.Method.GPAY_UPI).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            order_col = pay_qs.filter(order__isnull=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            credit_col = pay_qs.filter(order__isnull=True).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            total_col = cash + upi

            # Expenses
            exp_qs = DriverExpense.objects.filter(
                driver=d,
                date__gte=start_date,
                date__lte=end_date,
            )
            total_exp = exp_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
            net_col = total_col - total_exp

            grand_total_collected += total_col
            grand_total_expenses += total_exp
            grand_net_collected += net_col

            results.append({
                "driver_id": str(d.id),
                "driver_name": d.user.get_full_name() or d.user.username,
                "phone_number": d.phone_number,
                "vehicle_number": d.vehicle_number,
                "route_id": str(d.assigned_route.id) if d.assigned_route else None,
                "route_name": d.assigned_route.name if d.assigned_route else "Unassigned",
                "orders_delivered": orders_delivered,
                "cash_collected": cash,
                "upi_collected": upi,
                "order_payment_collected": order_col,
                "previous_credit_collected": credit_col,
                "total_collected": total_col,
                "expenses": total_exp,
                "net_collection": net_col,
            })

        return Response({
            "start_date": str(start_date),
            "end_date": str(end_date),
            "date_preset": preset_name,
            "grand_totals": {
                "total_collected": grand_total_collected,
                "total_expenses": grand_total_expenses,
                "net_collection": grand_net_collected,
            },
            "drivers": results,
        })


class DailyFinancialSummaryView(APIView):
    """
    Daily Financial Summary based on verified database calculations:
    Sales, Collections (Cash + UPI), Credit generated, Previous credit collected, Today's order collected, Driver expenses, Net collection, Receivables.
    """
    permission_classes = [permissions.IsAuthenticated, IsManagerOrOwner]

    @extend_schema(responses={200: drf_serializers.DictField()})
    def get(self, request):
        from apps.credits.models import CreditTransaction
        start_date, end_date, preset_name = resolve_date_range(request)

        # Sales
        orders_qs = Order.objects.filter(order_date__gte=start_date, order_date__lte=end_date).exclude(status=Order.Status.CANCELLED)
        total_sales = orders_qs.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        total_orders_count = orders_qs.count()

        # Collections
        pay_qs = Payment.objects.filter(
            received_at__date__gte=start_date,
            received_at__date__lte=end_date,
            status=Payment.Status.COMPLETED,
        )
        cash_collected = pay_qs.filter(payment_method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        upi_collected = pay_qs.filter(payment_method=Payment.Method.GPAY_UPI).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        total_collected = cash_collected + upi_collected

        today_order_collected = pay_qs.filter(order__isnull=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        previous_credit_collected = pay_qs.filter(order__isnull=True).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Driver Expenses
        exp_qs = DriverExpense.objects.filter(date__gte=start_date, date__lte=end_date)
        driver_expenses = exp_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Net Collection = Collections - Driver Expenses
        net_collection = total_collected - driver_expenses

        # Credit generated from credit sales in period
        credit_sales = CreditTransaction.objects.filter(
            transaction_type=CreditTransaction.TransactionType.CREDIT_SALE,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Active customer current balance snapshot
        total_receivable = Customer.objects.filter(is_active=True).aggregate(total=Sum("current_balance"))["total"] or Decimal("0.00")

        return Response({
            "start_date": str(start_date),
            "end_date": str(end_date),
            "date_preset": preset_name,
            "sales": total_sales,
            "orders_count": total_orders_count,
            "total_collected": total_collected,
            "cash_collected": cash_collected,
            "upi_collected": upi_collected,
            "today_order_collected": today_order_collected,
            "previous_credit_collected": previous_credit_collected,
            "credit_generated": credit_sales,
            "driver_expenses": driver_expenses,
            "net_collection": net_collection,
            "total_receivable": total_receivable,
        })


class DailyClosingView(APIView):
    """
    Daily Closing Review & Submission endpoint for Manager and Owner.
    GET: Returns real-time financial & operational totals for the date, plus closing status.
    POST: Formally closes the day and snapshots figures without altering underlying transactions.
    """
    permission_classes = [permissions.IsAuthenticated, IsManagerOrOwner]

    def get(self, request):
        from apps.reports.models import DailyClosing
        from apps.credits.models import CreditTransaction

        today = timezone.localdate()
        date_param = request.query_params.get("date")
        target_date = today
        if date_param:
            try:
                target_date = datetime.datetime.strptime(date_param, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                target_date = today

        # Compute real live figures for target_date
        orders_qs = Order.objects.filter(order_date=target_date)
        active_orders = orders_qs.exclude(status=Order.Status.CANCELLED)
        total_orders = active_orders.count()
        total_sales = active_orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        total_shop_expense = active_orders.aggregate(total=Sum("shop_expense"))["total"] or Decimal("0.00")

        payments_qs = Payment.objects.filter(received_at__date=target_date, status=Payment.Status.COMPLETED)
        cash_collected = payments_qs.filter(payment_method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        upi_collected = payments_qs.filter(payment_method=Payment.Method.GPAY_UPI).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        total_collected = cash_collected + upi_collected

        today_order_collected = payments_qs.filter(order__isnull=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        previous_credit_collected = payments_qs.filter(order__isnull=True).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        expenses_qs = DriverExpense.objects.filter(date=target_date)
        driver_expenses = expenses_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        net_collection = total_collected - driver_expenses

        # Credit generated
        credit_generated = CreditTransaction.objects.filter(
            transaction_type=CreditTransaction.TransactionType.CREDIT_SALE,
            created_at__date=target_date,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        deliveries_qs = Delivery.objects.filter(order__order_date=target_date)
        total_deliveries = deliveries_qs.count()
        delivered_count = deliveries_qs.filter(status=Delivery.Status.DELIVERED).count()
        pending_deliveries = deliveries_qs.filter(status__in=[Delivery.Status.ASSIGNED, Delivery.Status.IN_TRANSIT]).count()
        not_delivered_count = deliveries_qs.filter(status__in=[Delivery.Status.NOT_DELIVERED, Delivery.Status.FAILED]).count()

        # Check existing closing record
        closing_obj = DailyClosing.objects.filter(date=target_date).first()
        closing_record = None
        is_opened = False
        opening_record = None
        opening_cash = Decimal("0.00")

        if closing_obj:
            is_opened = closing_obj.is_opened
            opening_cash = closing_obj.opening_cash
            if closing_obj.is_opened:
                opening_record = {
                    "is_opened": closing_obj.is_opened,
                    "opened_by_name": closing_obj.opened_by.get_full_name() or closing_obj.opened_by.username if closing_obj.opened_by else "Staff",
                    "opened_at": closing_obj.opened_at,
                    "opening_cash": str(closing_obj.opening_cash),
                    "opening_notes": closing_obj.opening_notes,
                }
            if closing_obj.is_closed:
                closing_record = {
                    "id": str(closing_obj.id),
                    "date": str(closing_obj.date),
                    "is_closed": closing_obj.is_closed,
                    "closed_by_name": closing_obj.closed_by.get_full_name() or closing_obj.closed_by.username if closing_obj.closed_by else "Staff",
                    "closed_at": closing_obj.closed_at,
                    "reopened_by_name": closing_obj.reopened_by.get_full_name() or closing_obj.reopened_by.username if closing_obj.reopened_by else None,
                    "reopened_at": closing_obj.reopened_at,
                    "reopen_reason": closing_obj.reopen_reason,
                    "notes": closing_obj.notes,
                    "snapshot": {
                        "total_orders": closing_obj.total_orders,
                        "total_sales": closing_obj.total_sales,
                        "total_collected": closing_obj.total_collected,
                        "cash_collected": closing_obj.cash_collected,
                        "upi_collected": closing_obj.upi_collected,
                        "credit_generated": closing_obj.credit_generated,
                        "previous_credit_collected": closing_obj.previous_credit_collected,
                        "driver_expenses": closing_obj.driver_expenses,
                        "net_collection": closing_obj.net_collection,
                    }
                }

        expected_cash_in_hand = opening_cash + cash_collected - driver_expenses

        return Response({
            "date": str(target_date),
            "is_opened": is_opened,
            "opening_record": opening_record,
            "is_closed": closing_obj.is_closed if closing_obj else False,
            "closing_record": closing_record,
            "figures": {
                "opening_cash": str(opening_cash),
                "expected_cash_in_hand": str(expected_cash_in_hand),
                "total_orders": total_orders,
                "total_sales": str(total_sales),
                "total_shop_expense": str(total_shop_expense),
                "total_collected": str(total_collected),
                "cash_collected": str(cash_collected),
                "upi_collected": str(upi_collected),
                "credit_generated": str(credit_generated),
                "today_order_collected": str(today_order_collected),
                "previous_credit_collected": str(previous_credit_collected),
                "driver_expenses": str(driver_expenses),
                "net_collection": str(net_collection),
                "total_deliveries": total_deliveries,
                "delivered_count": delivered_count,
                "pending_deliveries": pending_deliveries,
                "not_delivered_count": not_delivered_count,
            }
        })

    def post(self, request):
        from apps.reports.models import DailyClosing
        from apps.credits.models import CreditTransaction

        today = timezone.localdate()
        date_param = request.data.get("date")
        target_date = today
        if date_param:
            try:
                target_date = datetime.datetime.strptime(date_param, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                target_date = today

        notes = request.data.get("notes", "")

        existing = DailyClosing.objects.filter(date=target_date, is_closed=True).first()
        if existing:
            return Response(
                {"detail": f"Day {target_date} has already been closed. Only an Owner can reopen a closed day."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Compute live figures
        orders_qs = Order.objects.filter(order_date=target_date)
        total_orders = orders_qs.count()
        total_sales = orders_qs.exclude(status=Order.Status.CANCELLED).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

        payments_qs = Payment.objects.filter(received_at__date=target_date, status=Payment.Status.COMPLETED)
        cash_collected = payments_qs.filter(payment_method=Payment.Method.CASH).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        upi_collected = payments_qs.filter(payment_method=Payment.Method.GPAY_UPI).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        total_collected = cash_collected + upi_collected

        previous_credit_collected = payments_qs.filter(order__isnull=True).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        expenses_qs = DriverExpense.objects.filter(date=target_date)
        driver_expenses = expenses_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        net_collection = total_collected - driver_expenses

        credit_generated = CreditTransaction.objects.filter(
            transaction_type=CreditTransaction.TransactionType.CREDIT_SALE,
            created_at__date=target_date,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        closing, _ = DailyClosing.objects.update_or_create(
            date=target_date,
            defaults={
                "is_closed": True,
                "closed_by": request.user,
                "closed_at": timezone.now(),
                "total_orders": total_orders,
                "total_sales": total_sales,
                "total_collected": total_collected,
                "cash_collected": cash_collected,
                "upi_collected": upi_collected,
                "credit_generated": credit_generated,
                "previous_credit_collected": previous_credit_collected,
                "driver_expenses": driver_expenses,
                "net_collection": net_collection,
                "notes": notes,
                "reopened_by": None,
                "reopened_at": None,
                "reopen_reason": "",
            }
        )

        from apps.common.audit import log_activity
        log_activity(
            user=request.user,
            action="CLOSED",
            entity_type="DAILY_CLOSING",
            entity_id=closing.id,
            entity_name=f"Daily Closing ({target_date})",
            summary=f"Closed business day {target_date}: Sales ₹{total_sales}, Collected ₹{total_collected}, Net ₹{net_collection}",
            details={
                "date": str(target_date),
                "total_sales": str(total_sales),
                "total_collected": str(total_collected),
                "net_collection": str(net_collection),
            }
        )

        return Response({
            "message": f"Daily closing for {target_date} confirmed successfully.",
            "date": str(target_date),
            "is_closed": True,
            "closed_at": closing.closed_at,
        }, status=status.HTTP_201_CREATED)


class ReopenDailyClosingView(APIView):
    """
    Controlled Owner-only action to reopen a closed day.
    Managers are strictly forbidden from performing this action (HTTP 403).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.reports.models import DailyClosing

        if request.user.role != "OWNER" and not request.user.is_superuser:
            return Response(
                {"detail": "Only the business Owner has authorization to reopen a closed business day."},
                status=status.HTTP_403_FORBIDDEN,
            )

        today = timezone.localdate()
        date_param = request.data.get("date")
        target_date = today
        if date_param:
            try:
                target_date = datetime.datetime.strptime(date_param, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                target_date = today

        reason = request.data.get("reason", "").strip()
        if not reason:
            return Response(
                {"detail": "A reason is required to reopen a closed business day."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        closing = DailyClosing.objects.filter(date=target_date, is_closed=True).first()
        if not closing:
            return Response(
                {"detail": f"No closed day record found for {target_date}."},
                status=status.HTTP_404_NOT_FOUND,
            )

        closing.is_closed = False
        closing.reopened_by = request.user
        closing.reopened_at = timezone.now()
        closing.reopen_reason = reason
        closing.save()

        from apps.common.audit import log_activity
        log_activity(
            user=request.user,
            action="REOPENED",
            entity_type="DAILY_CLOSING",
            entity_id=closing.id,
            entity_name=f"Reopened Daily Closing ({target_date})",
            summary=f"Owner reopened business day {target_date}: {reason}",
            details={"date": str(target_date), "reason": reason},
        )

        return Response({
            "message": f"Business day {target_date} has been reopened.",
            "date": str(target_date),
            "is_closed": False,
            "reopened_at": closing.reopened_at,
        }, status=status.HTTP_200_OK)


class DailyOpenView(APIView):
    """
    Day Opening endpoint for Manager and Owner to start the business day.
    POST: Formally opens the day with opening cash float in register/drawer.
    """
    permission_classes = [permissions.IsAuthenticated, IsManagerOrOwner]

    def post(self, request):
        from apps.reports.models import DailyClosing

        today = timezone.localdate()
        date_param = request.data.get("date")
        target_date = today
        if date_param:
            try:
                target_date = datetime.datetime.strptime(date_param, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                target_date = today

        opening_cash_raw = request.data.get("opening_cash", "0.00")
        try:
            opening_cash = Decimal(str(opening_cash_raw)).quantize(Decimal("0.01"))
        except:
            opening_cash = Decimal("0.00")

        notes = request.data.get("notes", "")

        existing = DailyClosing.objects.filter(date=target_date, is_closed=True).first()
        if existing:
            return Response(
                {"detail": f"Day {target_date} has already been closed. Reopen the day before modifying."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        closing_obj, _ = DailyClosing.objects.update_or_create(
            date=target_date,
            defaults={
                "is_opened": True,
                "opened_by": request.user,
                "opened_at": timezone.now(),
                "opening_cash": opening_cash,
                "opening_notes": notes,
                "is_closed": False,
            }
        )

        from apps.common.audit import log_activity
        log_activity(
            user=request.user,
            action="CREATED",
            entity_type="REPORT",
            entity_id=closing_obj.id,
            entity_name=f"Day Opened: {target_date}",
            summary=f"Opened business day for {target_date} with opening cash float of ₹{opening_cash}",
            details={"date": str(target_date), "opening_cash": str(opening_cash), "notes": notes},
        )

        return Response({
            "message": f"Successfully opened day for {target_date} with opening float of ₹{opening_cash}.",
            "date": str(target_date),
            "is_opened": True,
            "opening_cash": str(opening_cash),
            "opened_at": closing_obj.opened_at,
            "opened_by_name": request.user.get_full_name() or request.user.username,
        }, status=status.HTTP_200_OK)


