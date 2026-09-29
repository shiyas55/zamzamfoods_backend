from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ActivityLogViewSet, health_check, SystemSettingsView

router = DefaultRouter()
router.register(r"activity-logs", ActivityLogViewSet, basename="activity-log")
router.register(r"activity-history", ActivityLogViewSet, basename="activity-history")

urlpatterns = [
    path("settings/", SystemSettingsView.as_view(), name="system_settings"),
] + router.urls
