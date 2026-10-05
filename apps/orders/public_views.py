from rest_framework import views, status
from rest_framework.response import Response
from apps.customers.models import Customer
from apps.products.models import Product
from apps.orders.serializers import CreateOrderSerializer
from apps.customers.services import get_effective_product_price
from apps.common.models import SystemSettings

class PublicCustomerOrderView(views.APIView):
    """
    Unauthenticated endpoint for the customer self-order link.
    Requires a valid Customer UUID.
    GET: Returns shop details and available products with customer-specific pricing.
    POST: Submits the order directly, locking it immediately.
    Enforces master is_self_order_enabled setting configured by Owner/Admin.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(id=customer_id, is_active=True)
        except Customer.DoesNotExist:
            return Response({"error": "Invalid or inactive customer link."}, status=status.HTTP_404_NOT_FOUND)

        sys_settings = SystemSettings.get_settings()
        if sys_settings.is_maintenance_mode:
            return Response({
                "error": sys_settings.maintenance_message or "System is currently undergoing scheduled maintenance. Please check back shortly.",
                "is_maintenance_mode": True,
                "business_name": sys_settings.business_name,
                "phone_number": sys_settings.phone_number,
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not sys_settings.is_self_order_enabled:
            return Response({
                "error": "Online self-ordering is currently turned off by the shop administration. Please contact the shop directly.",
                "is_self_order_enabled": False,
                "business_name": sys_settings.business_name,
                "phone_number": sys_settings.phone_number,
            }, status=status.HTTP_403_FORBIDDEN)

        products = Product.objects.filter(is_active=True)
        products_data = []
        for p in products:
            price, _, _ = get_effective_product_price(customer, p)
            products_data.append({
                "id": str(p.id),
                "name": p.name,
                "code": p.code,
                "unit": getattr(p, "packet_size", "") or "Pcs",
                "price": str(price)
            })

        data = {
            "customer": {
                "id": str(customer.id),
                "name": customer.name,
                "owner_name": customer.owner_name,
                "address": customer.address,
                "phone": customer.phone,
                "current_balance": str(customer.current_balance),
            },
            "products": products_data,
            "settings": {
                "business_name": sys_settings.business_name,
                "phone_number": sys_settings.phone_number,
                "gst_number": sys_settings.gst_number,
                "is_whatsapp_enabled": sys_settings.is_whatsapp_enabled,
                "is_self_order_enabled": sys_settings.is_self_order_enabled,
                "is_maintenance_mode": sys_settings.is_maintenance_mode,
                "maintenance_message": sys_settings.maintenance_message,
            }
        }
        return Response(data)

    def post(self, request, customer_id):
        try:
            customer = Customer.objects.get(id=customer_id, is_active=True)
        except Customer.DoesNotExist:
            return Response({"error": "Invalid or inactive customer link."}, status=status.HTTP_404_NOT_FOUND)

        sys_settings = SystemSettings.get_settings()
        if sys_settings.is_maintenance_mode:
            return Response({
                "error": sys_settings.maintenance_message or "System is currently undergoing scheduled maintenance. Please check back shortly.",
                "is_maintenance_mode": True,
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not sys_settings.is_self_order_enabled:
            return Response({
                "error": f"Online self-ordering is currently turned off by the shop administration. Please contact the shop directly at {sys_settings.phone_number}.",
                "is_self_order_enabled": False,
            }, status=status.HTTP_403_FORBIDDEN)

        # IP rate limiting protection
        from django.core.cache import cache
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "unknown")
        cache_key = f"public_order_rate_{ip}"
        recent_orders = cache.get(cache_key, 0)
        if recent_orders >= 30:
            return Response(
                {"error": "Too many orders submitted in a short period. Please wait a minute before submitting again."},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        cache.set(cache_key, recent_orders + 1, timeout=60)

        # Inject source and identities
        data = request.data.copy()
        data["customer_id"] = str(customer.id)
        data["source"] = "CUSTOMER_LINK"
        data["entered_by_role"] = "CUSTOMER"
        data["entered_by_name"] = customer.name
        data["entered_by_type"] = "CUSTOMER"

        serializer = CreateOrderSerializer(data=data, context={"request": None})
        if serializer.is_valid():
            order = serializer.save()
            return Response({
                "message": "Order submitted successfully.",
                "order_number": order.order_number,
                "order_id": str(order.id)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

