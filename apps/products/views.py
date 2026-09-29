from rest_framework import viewsets, permissions
from apps.common.permissions import IsOwner, IsManagerOrOwner
from .models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ModelViewSet):
    """
    Endpoints for products (Kubbus, Romali, etc.)
    - All authenticated users can read.
    - Only Owner/Manager can modify products.
    """
    queryset = Product.objects.all().order_by("name")
    serializer_class = ProductSerializer

    def get_permissions(self):
        if self.action in ["create", "destroy"]:
            return [IsOwner()]
        if self.action in ["update", "partial_update"]:
            return [IsManagerOrOwner()]
        return [permissions.IsAuthenticated()]
