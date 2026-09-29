from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet
from .public_views import PublicCustomerOrderView

router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="order")

urlpatterns = [
    path("public/customer-order/<uuid:customer_id>/", PublicCustomerOrderView.as_view(), name="public-customer-order"),
    path("orders/public/customer-order/<uuid:customer_id>/", PublicCustomerOrderView.as_view(), name="public-customer-order-alt"),
    path("", include(router.urls)),
]
