from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreditTransactionViewSet

router = DefaultRouter()
router.register(r"credits", CreditTransactionViewSet, basename="credit")

urlpatterns = [
    path("", include(router.urls)),
]
