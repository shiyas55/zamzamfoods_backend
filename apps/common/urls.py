from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    ActivityLogViewSet,
    health_check,
    SystemSettingsView,
    VerifySettingsPinView,
    ResetSettingsPinView,
    DatabaseStatsView,
    DatabaseBackupView,
    DatabaseRestoreView,
    DatabaseClearAllView,
    BusinessDocumentViewSet,
)

router = DefaultRouter()
router.register(r"activity-logs", ActivityLogViewSet, basename="activity-log")
router.register(r"activity-history", ActivityLogViewSet, basename="activity-history")
router.register(r"business-documents", BusinessDocumentViewSet, basename="business-document")

urlpatterns = [
    path("settings/", SystemSettingsView.as_view(), name="system_settings"),
    path("settings/verify-pin/", VerifySettingsPinView.as_view(), name="verify_settings_pin"),
    path("settings/reset-pin/", ResetSettingsPinView.as_view(), name="reset_settings_pin"),
    path("database/stats/", DatabaseStatsView.as_view(), name="database_stats"),
    path("database/backup/", DatabaseBackupView.as_view(), name="database_backup"),
    path("database/restore/", DatabaseRestoreView.as_view(), name="database_restore"),
    path("database/clear-all/", DatabaseClearAllView.as_view(), name="database_clear_all"),
] + router.urls

