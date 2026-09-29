from django.urls import path
from .views import (
    DashboardSummaryView,
    OutstandingCreditReportView,
    CollectionReportView,
    DriverCollectionReportView,
    DailyFinancialSummaryView,
    DriverPerformanceReportView,
    DriverDetailReportView,
    DailyClosingView,
    ReopenDailyClosingView,
    DailyOpenView,
)

urlpatterns = [
    path("dashboard/", DashboardSummaryView.as_view(), name="dashboard_summary"),
    path("outstanding-credit/", OutstandingCreditReportView.as_view(), name="outstanding_credit_report"),
    path("collections/", CollectionReportView.as_view(), name="collections_report"),
    path("driver-collections/", DriverCollectionReportView.as_view(), name="driver_collections_report"),
    path("financial-summary/", DailyFinancialSummaryView.as_view(), name="financial_summary"),
    path("driver-performance/", DriverPerformanceReportView.as_view(), name="driver_performance_report"),
    path("driver-performance/<uuid:driver_id>/", DriverDetailReportView.as_view(), name="driver_detail_report"),
    path("daily-closing/", DailyClosingView.as_view(), name="daily_closing"),
    path("daily-closing/reopen/", ReopenDailyClosingView.as_view(), name="reopen_daily_closing"),
    path("daily-open/", DailyOpenView.as_view(), name="daily_open"),
]

