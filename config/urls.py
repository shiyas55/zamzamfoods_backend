"""
Zamzam Foods Main URL Configuration.
API versioning: /api/v1/
Modular routing with OpenAPI 3.0 schema and Swagger/Redoc documentation.
"""

from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from apps.common.views import health_check

# Customize Admin Site Branding
admin.site.site_header = "Zamzam Foods Administration"
admin.site.site_title = "Zamzam Foods Portal"
admin.site.index_title = "Operations & Financial Management"

api_v1_patterns = [
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.routes.urls")),
    path("", include("apps.customers.urls")),
    path("", include("apps.products.urls")),
    path("", include("apps.orders.urls")),
    path("", include("apps.deliveries.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.credits.urls")),
    path("", include("apps.common.urls")),
    path("reports/", include("apps.reports.urls")),
    path("whatsapp/", include("apps.whatsapp.urls")),

    # API Documentation
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    # Public health check — used by Koyeb to verify container liveness
    path("api/health/", health_check, name="health_check"),
    # Direct Meta Webhook endpoint (/api/whatsapp/webhook/)
    path("api/whatsapp/", include("apps.whatsapp.urls")),
    path("api/v1/", include((api_v1_patterns, "api_v1"))),
]
