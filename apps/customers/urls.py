from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, CustomerProductPriceViewSet, CustomerDocumentViewSet

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"customer-prices", CustomerProductPriceViewSet, basename="customer-price")
router.register(r"customer-documents", CustomerDocumentViewSet, basename="customer-document")

urlpatterns = [
    path("", include(router.urls)),
]
