from decimal import Decimal
from django.db.models import Sum, Count, Prefetch, Q
from django.utils import timezone
from rest_framework import viewsets, permissions, filters, status, serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from apps.common.permissions import IsManagerOrOwner
from apps.products.models import Product
from .models import Customer, CustomerProductPrice, CustomerDocument
from .serializers import (
    CustomerSerializer,
    CustomerProductPriceSerializer,
    SetCustomerPriceInputSerializer,
    CustomerPricingOverviewItemSerializer,
    CustomerDetailSummarySerializer,
    CustomerDocumentSerializer,
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

        today = timezone.localdate()
        active_prices_pref = Prefetch(
            "custom_prices",
            queryset=CustomerProductPrice.objects.filter(
                is_active=True,
                effective_from__lte=today,
            ).filter(
                Q(effective_to__isnull=True) | Q(effective_to__gte=today)
            ).order_by("effective_from", "created_at"),
            to_attr="prefetched_custom_prices",
        )
        queryset = Customer.objects.select_related("route").prefetch_related(active_prices_pref).all()

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

    def destroy(self, request, *args, **kwargs):
        from django.db.models import ProtectedError
        instance = self.get_object()
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    "detail": "Cannot delete this customer shop because it has existing orders, payments, or delivery history. You can deactivate the shop instead to maintain financial audit integrity."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

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

    @extend_schema(responses={200: drf_serializers.DictField()})
    @action(detail=True, methods=["post"], url_path="set-balance", permission_classes=[IsManagerOrOwner])
    def set_balance(self, request, pk=None):
        """
        Directly sets the customer's current balance / previous due from Fast Order Entry.
        Creates an audit ledger adjustment record and updates current_balance in DB.
        """
        customer = self.get_object()
        balance_raw = request.data.get("balance")
        if balance_raw is None:
            return Response({"detail": "balance field is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            new_balance = Decimal(str(balance_raw)).quantize(Decimal("0.01"))
            if new_balance < 0:
                return Response({"detail": "Balance cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({"detail": "Invalid balance format."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.credits.services import record_adjustment_service
        delta = (new_balance - customer.current_balance).quantize(Decimal("0.01"))
        if delta != Decimal("0.00"):
            record_adjustment_service(
                customer_id=customer.id,
                amount=delta,
                notes=request.data.get("notes") or f"Previous due set to ₹{new_balance} from Fast Wholesale Entry",
                recorded_by=request.user,
            )
        customer.refresh_from_db()
        return Response({
            "id": str(customer.id),
            "name": customer.name,
            "current_balance": str(customer.current_balance),
        }, status=status.HTTP_200_OK)


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
        customer = serializer.validated_data.get("customer")
        product = serializer.validated_data.get("product")
        if customer and product and serializer.validated_data.get("is_active", True):
            CustomerProductPrice.objects.filter(
                customer=customer,
                product=product,
                is_active=True
            ).update(is_active=False, updated_by=self.request.user)
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class CustomerDocumentViewSet(viewsets.ModelViewSet):
    """
    CRUD and multi-file batch upload for shop documents (licenses, certificates, KYC, photos, etc.)
    """
    serializer_class = CustomerDocumentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "title",
        "file_name",
        "document_number",
        "notes",
        "customer__name",
        "customer__route__name",
    ]
    ordering_fields = ["created_at", "expiry_date", "title", "file_size", "customer__name"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "batch_upload"]:
            return [IsManagerOrOwner()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return CustomerDocument.objects.none()

        queryset = CustomerDocument.objects.select_related("customer", "customer__route", "uploaded_by").all()

        # Driver data isolation: driver ONLY sees documents for shops on their assigned route
        if user.role == "DRIVER":
            from apps.routes.models import Driver
            try:
                driver_profile = user.driver_profile
                if driver_profile.assigned_route:
                    queryset = queryset.filter(customer__route=driver_profile.assigned_route)
                else:
                    return CustomerDocument.objects.none()
            except Driver.DoesNotExist:
                return CustomerDocument.objects.none()

        # Customer filter
        customer_id = self.request.query_params.get("customer")
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)

        # Route filter
        route_id = self.request.query_params.get("route")
        if route_id:
            queryset = queryset.filter(customer__route_id=route_id)

        # Document type filter
        doc_type = self.request.query_params.get("document_type")
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)

        # Expired filter
        is_expired = self.request.query_params.get("is_expired")
        today = timezone.localdate()
        if is_expired == "true":
            queryset = queryset.filter(expiry_date__lt=today)
        elif is_expired == "false":
            queryset = queryset.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))

        return queryset

    def perform_create(self, serializer):
        uploaded_file = self.request.FILES.get("file")
        file_name = uploaded_file.name if uploaded_file else ""
        file_size = uploaded_file.size if uploaded_file else 0
        mime_type = getattr(uploaded_file, "content_type", "") if uploaded_file else ""
        title = serializer.validated_data.get("title") or file_name or "Shop Document"

        serializer.save(
            title=title,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by=self.request.user,
        )

    @action(detail=False, methods=["post"], url_path="batch-upload")
    def batch_upload(self, request):
        """
        Upload multiple files at once for a customer shop.
        Accepts multipart/form-data:
        - customer: UUID
        - document_type: string (optional, defaults to 'OTHER')
        - title: optional title or prefix
        - document_number: optional string
        - expiry_date: optional date string (YYYY-MM-DD)
        - notes: optional string
        - files: list of uploaded files (one or more)
        """
        customer_id = request.data.get("customer")
        if not customer_id:
            return Response({"detail": "Customer ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({"detail": "Customer not found."}, status=status.HTTP_404_NOT_FOUND)

        uploaded_files = request.FILES.getlist("files")
        if not uploaded_files:
            single_file = request.FILES.get("file")
            if single_file:
                uploaded_files = [single_file]
            else:
                return Response({"detail": "No files provided for upload."}, status=status.HTTP_400_BAD_REQUEST)

        doc_type = request.data.get("document_type") or CustomerDocument.DocumentType.OTHER
        base_title = request.data.get("title", "").strip()
        document_number = request.data.get("document_number", "").strip()
        expiry_date = request.data.get("expiry_date") or None
        notes = request.data.get("notes", "").strip()

        created_docs = []
        for idx, f in enumerate(uploaded_files):
            file_title = base_title
            if not file_title:
                file_title = f.name
            elif len(uploaded_files) > 1:
                file_title = f"{base_title} ({idx + 1})"

            doc = CustomerDocument.objects.create(
                customer=customer,
                title=file_title,
                document_type=doc_type,
                file=f,
                file_name=f.name,
                file_size=f.size,
                mime_type=getattr(f, "content_type", ""),
                document_number=document_number,
                expiry_date=expiry_date,
                notes=notes,
                uploaded_by=request.user,
            )
            created_docs.append(doc)

        serializer = self.get_serializer(created_docs, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

