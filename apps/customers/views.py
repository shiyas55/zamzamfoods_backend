from decimal import Decimal
from django.db.models import Sum, Count
from rest_framework import viewsets, permissions, filters, status, serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.common.permissions import IsManagerOrOwner
from apps.products.models import Product
from .models import Customer, CustomerProductPrice
from .serializers import (
    CustomerSerializer,
    CustomerProductPriceSerializer,
    SetCustomerPriceInputSerializer,
    CustomerPricingOverviewItemSerializer,
    CustomerDetailSummarySerializer,
)
from .services import get_effective_product_price, set_customer_product_price

class CustomerViewSet(viewsets.ModelViewSet):
    """
    CRUD for customer shops.
    - Owner & Manager: Full access across all routes.
    - Driver: Isolated strictly to shops on their assigned route.
    """
    serializer_class = CustomerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "owner_name", "phone", "address", "landmark"]
    ordering_fields = ["name", "current_balance", "created_at"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManagerOrOwner()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Customer.objects.none()

        queryset = Customer.objects.select_related("route").all()

        # Route filter query param (for managers/owners)
        route_id = self.request.query_params.get("route")
        if route_id and (user.is_superuser or user.role in ["OWNER", "MANAGER"]):
            queryset = queryset.filter(route_id=route_id)

        # Driver data isolation: driver ONLY sees shops on their assigned route
        if user.role == "DRIVER":
            if hasattr(user, "driver_profile") and user.driver_profile and user.driver_profile.assigned_route:
                queryset = queryset.filter(route=user.driver_profile.assigned_route)
            else:
                return Customer.objects.none()

        return queryset.order_by("route__name", "name")

    @extend_schema(responses={200: CustomerPricingOverviewItemSerializer(many=True)})
    @action(detail=True, methods=["get", "post"], url_path="pricing")
    def pricing(self, request, pk=None):
        """
        GET: Returns pricing for all active products for this customer (custom or default).
        POST: Sets or updates custom wholesale price for a product. (Manager/Owner only)
        """
        customer = self.get_object()

        if request.method == "POST":
            if request.user.role not in ["OWNER", "MANAGER"] and not request.user.is_superuser:
                return Response({"detail": "Only Owners and Managers can configure customer pricing."}, status=status.HTTP_403_FORBIDDEN)

            serializer = SetCustomerPriceInputSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            new_price = set_customer_product_price(
                customer_id=customer.id,
                product_id=data["product_id"],
                price=data["price"],
                effective_from=data.get("effective_from"),
                effective_to=data.get("effective_to"),
                user=request.user,
            )
            return Response(CustomerProductPriceSerializer(new_price).data, status=status.HTTP_201_CREATED)

        # GET: List pricing for all active products
        products = Product.objects.filter(is_active=True).order_by("name")
        results = []
        for p in products:
            effective_price, is_custom, price_id = get_effective_product_price(customer, p)
            results.append({
                "product_id": str(p.id),
                "product_name": p.name,
                "product_code": p.code,
                "packet_size": p.packet_size,
                "default_price": p.unit_price,
                "effective_price": effective_price,
                "has_custom_price": is_custom,
                "price_id": price_id,
                "is_active": True,
            })
        return Response(results)

    @extend_schema(responses={200: drf_serializers.DictField()})
    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        """
        Returns full operational and financial summary for this customer shop:
        - Basic totals (orders, sales, paid, balance)
        - Last order with current pricing comparison (for repeat ordering)
        - Frequent order information (most ordered product, typical quantity)
        - Recent orders, payments, and deliveries
        """
        customer = self.get_object()
        from apps.orders.models import Order, OrderItem
        from apps.payments.models import Payment
        from apps.deliveries.models import Delivery
        from apps.customers.services import get_effective_product_price

        orders = customer.orders.exclude(status=Order.Status.CANCELLED).order_by("-order_date", "-created_at")
        total_orders = orders.count()
        total_sales = orders.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")

        payments = customer.payments.filter(status=Payment.Status.COMPLETED).order_by("-received_at")
        total_paid = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Last Order Information with Current Pricing Resolution
        last_order_obj = orders.first()
        last_order = None
        if last_order_obj:
            last_order_items = []
            for it in last_order_obj.items.select_related("product").all():
                current_price, is_custom, _ = get_effective_product_price(customer, it.product)
                last_order_items.append({
                    "product_id": str(it.product.id),
                    "product_name": it.product.name,
                    "product_code": it.product.code,
                    "packet_size": it.product.packet_size,
                    "quantity": it.quantity,
                    "historical_unit_price": it.unit_price,
                    "current_unit_price": current_price,
                    "price_changed": it.unit_price != current_price,
                })

            last_order = {
                "id": str(last_order_obj.id),
                "order_number": last_order_obj.order_number,
                "order_date": last_order_obj.order_date,
                "total_amount": last_order_obj.total_amount,
                "status": last_order_obj.status,
                "items": last_order_items,
            }

        # Frequent Order Information
        frequent_product_stats = (
            OrderItem.objects.filter(order__customer=customer)
            .exclude(order__status=Order.Status.CANCELLED)
            .values("product__name")
            .annotate(
                order_occurrences=Count("id"),
                total_qty=Sum("quantity"),
            )
            .order_by("-order_occurrences")
            .first()
        )

        most_frequent_product = "None"
        typical_quantity = 0
        if frequent_product_stats and frequent_product_stats["order_occurrences"] > 0:
            most_frequent_product = frequent_product_stats["product__name"]
            typical_quantity = round(
                frequent_product_stats["total_qty"] / frequent_product_stats["order_occurrences"]
            )

        frequent_order_info = {
            "most_frequent_product": most_frequent_product,
            "typical_quantity": typical_quantity,
            "total_orders": total_orders,
            "last_order_date": last_order_obj.order_date if last_order_obj else None,
        }

        # Recent orders (full historical details including product details, source, and delivery status)
        recent_orders = [
            {
                "id": str(o.id),
                "order_number": o.order_number,
                "order_date": str(o.order_date),
                "status": o.status,
                "total_amount": str(o.total_amount),
                "source": o.source,
                "delivery_status": o.delivery.status if hasattr(o, "delivery") and o.delivery else "ASSIGNED",
                "items": [
                    {
                        "id": str(it.id),
                        "product": str(it.product.id),
                        "product_name": it.product.name,
                        "product_details": {
                            "id": str(it.product.id),
                            "name": it.product.name,
                            "code": it.product.code,
                            "packet_size": it.product.packet_size or "",
                            "unit_price": str(it.unit_price),
                            "is_active": it.product.is_active,
                        },
                        "quantity": it.quantity,
                        "unit_price": str(it.unit_price),
                        "subtotal": str(it.subtotal),
                    }
                    for it in o.items.select_related("product").all()
                ],
            }
            for o in orders.select_related("delivery")[:100]
        ]

        # Recent payments
        recent_payments = [
            {
                "id": str(p.id),
                "payment_number": p.payment_number,
                "amount": p.amount,
                "payment_method": p.payment_method,
                "received_at": p.received_at,
                "status": p.status,
                "collected_by_name": p.collected_by.get_full_name() or p.collected_by.username if p.collected_by else "Staff",
            }
            for p in payments[:10]
        ]

        # Recent deliveries
        deliveries = Delivery.objects.filter(order__customer=customer).select_related("driver__user").order_by("-created_at")[:10]
        recent_deliveries = [
            {
                "id": str(d.id),
                "delivery_number": d.delivery_number,
                "order_number": d.order.order_number,
                "status": d.status,
                "failed_reason": d.failed_reason,
                "created_at": d.created_at,
                "driver_name": d.driver.user.get_full_name() or d.driver.user.username if d.driver and d.driver.user else "Assigned Driver",
            }
            for d in deliveries
        ]

        data = {
            "customer": CustomerSerializer(customer).data,
            "customer_id": str(customer.id),
            "customer_name": customer.name,
            "total_orders": total_orders,
            "total_sales": total_sales,
            "total_paid": total_paid,
            "current_balance": customer.current_balance,
            "credit_limit": customer.credit_limit,
            "is_credit_exceeded": customer.is_credit_exceeded,
            "last_order": last_order,
            "frequent_order_info": frequent_order_info,
            "recent_orders": recent_orders,
            "recent_payments": recent_payments,
            "recent_deliveries": recent_deliveries,
        }
        return Response(data)


class CustomerProductPriceViewSet(viewsets.ModelViewSet):
    """
    CRUD for customer-specific product wholesale prices.
    Only Owner and Manager can access or modify customer wholesale pricing.
    """
    serializer_class = CustomerProductPriceSerializer
    permission_classes = [IsManagerOrOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["customer__name", "product__name", "product__code"]
    ordering_fields = ["customer__name", "price", "effective_from", "created_at"]

    def get_queryset(self):
        queryset = CustomerProductPrice.objects.select_related("customer", "product").all()
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        product_id = self.request.query_params.get("product")
        if product_id:
            queryset = queryset.filter(product_id=product_id)

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset.order_by("customer__name", "product__name")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
