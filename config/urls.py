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

from django.conf import settings
from django.conf.urls.static import static

api_v1_patterns = [
    path("auth/", include("apps.accounts.urls")),
    path("", include("apps.accounts.urls")),
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
    path("docs/", SpectacularSwaggerView.as_view(url_name="api_v1:schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="api_v1:schema"), name="redoc"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    # Public health check — used by Koyeb to verify container liveness
    path("api/health/", health_check, name="health_check"),
    # Direct Meta Webhook endpoint (/api/whatsapp/webhook/)
    path("api/whatsapp/", include("apps.whatsapp.urls")),
    path("api/v1/", include((api_v1_patterns, "api_v1"))),
]

from django.views.static import serve
from django.urls import re_path

from pathlib import Path
from django.http import FileResponse, HttpResponse

def serve_spa(request, path=""):
    dist_dir = Path(settings.BASE_DIR) / "dist"
    if not dist_dir.exists():
        dist_dir = Path(settings.BASE_DIR).parent / "frontend" / "dist"
    
    if path:
        target_file = (dist_dir / path).resolve()
        if str(target_file).startswith(str(dist_dir.resolve())) and target_file.is_file():
            return FileResponse(open(target_file, "rb"))

    index_file = dist_dir / "index.html"
    if index_file.exists():
        return FileResponse(open(index_file, "rb"))

    return HttpResponse("<h1>Zamzam Foods API</h1><p>Visit <a href='/api/v1/'>/api/v1/</a></p>")

# Serve frontend single-page application for all non-API paths
urlpatterns += [
    re_path(r"^(?P<path>.*)$", serve_spa),
]

