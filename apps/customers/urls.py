from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, CustomerProductPriceViewSet

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"customer-prices", CustomerProductPriceViewSet, basename="customer-price")

urlpatterns = [
    path("", include(router.urls)),
]
