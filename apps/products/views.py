from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from apps.common.permissions import IsOwner, IsManagerOrOwner
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    """
    Endpoints for products (Kubbus, Romali, etc.)
    - All authenticated users can read.
    - Owner and Manager can create, update, or delete products.
    """
    queryset = Product.objects.all().order_by("name")
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ["create", "destroy", "update", "partial_update"]:
            return [IsManagerOrOwner()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        product = serializer.save()
        from apps.common.audit import log_activity
        log_activity(
            user=self.request.user,
            action="CREATED",
            entity_type="PRODUCT",
            entity_id=product.id,
            entity_name=product.name,
            summary=f"Created product '{product.name}' ({product.code}) at ₹{product.unit_price}",
        )

    def perform_update(self, serializer):
        product = serializer.save()
        from apps.common.audit import log_activity
        log_activity(
            user=self.request.user,
            action="UPDATED",
            entity_type="PRODUCT",
            entity_id=product.id,
            entity_name=product.name,
            summary=f"Updated product '{product.name}' ({product.code}) at ₹{product.unit_price}",
        )

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        order_item_count = product.order_items.count() if hasattr(product, "order_items") else 0
        if order_item_count > 0:
            return Response(
                {
                    "error": f"Cannot permanently delete '{product.name}' because {order_item_count} historical order item(s) reference it. Please set its status to Inactive instead."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.common.audit import log_activity
        log_activity(
            user=self.request.user,
            action="DELETED",
            entity_type="PRODUCT",
            entity_id=product.id,
            entity_name=product.name,
            summary=f"Deleted product '{product.name}' ({product.code})",
        )
        return super().destroy(request, *args, **kwargs)
