from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RouteViewSet, DriverViewSet, DriverExpenseViewSet, DriverShiftViewSet

router = DefaultRouter()
router.register(r"routes", RouteViewSet, basename="route")
router.register(r"drivers", DriverViewSet, basename="driver")
router.register(r"driver-expenses", DriverExpenseViewSet, basename="driver-expense")
router.register(r"driver-shifts", DriverShiftViewSet, basename="driver-shift")

urlpatterns = [
    path("", include(router.urls)),
]
