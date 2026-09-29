import re
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from apps.common.models import SystemSettings
from apps.common.authentication import CookieJWTAuthentication

EXEMPT_URL_PATTERNS = [
    re.compile(r"^/admin/"),
    re.compile(r"^/static/"),
    re.compile(r"^/media/"),
    re.compile(r"^/favicon\.ico$"),
    re.compile(r"^/api/v1/auth/"),
    re.compile(r"^/api/v1/settings/"),
]


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    Middleware that enforces master system-wide Maintenance Mode.
    
    When is_maintenance_mode is True:
      - Admin / Owner (role='OWNER' or is_superuser) can access all endpoints.
      - Auth endpoints remain open so Admins can log in and manage the system.
      - Settings endpoint remains open so frontend can read status and Owner can turn maintenance OFF.
      - Managers, Drivers, and Public Users receive HTTP 503 Service Unavailable.
    """

    def process_request(self, request):
        path = request.path_info or request.path

        # Check exempt URLs first
        for pattern in EXEMPT_URL_PATTERNS:
            if pattern.match(path):
                return None

        # Fetch settings
        try:
            sys_settings = SystemSettings.get_settings()
        except Exception:
            # During early migrations or DB issues, pass through
            return None

        if not sys_settings.is_maintenance_mode:
            return None

        # Maintenance mode is ACTIVE. Check if requester is Owner / Admin.
        user = getattr(request, "_force_auth_user", None) or getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            # Attempt DRF Cookie / Header JWT resolution
            try:
                from rest_framework.request import Request
                drf_request = Request(request)
                auth_res = CookieJWTAuthentication().authenticate(drf_request)
                if not auth_res:
                    auth_res = JWTAuthentication().authenticate(drf_request)
                if auth_res:
                    user = auth_res[0]
                    request.user = user
            except Exception:
                user = None

        if user and user.is_authenticated:
            role = getattr(user, "role", "")
            is_super = getattr(user, "is_superuser", False)
            if role == "OWNER" or is_super:
                # Owner has full uninterrupted access during maintenance
                return None

        # Non-owner request blocked during maintenance
        return JsonResponse(
            {
                "error": "System is currently undergoing scheduled maintenance.",
                "is_maintenance_mode": True,
                "maintenance_message": sys_settings.maintenance_message
                or "System is currently undergoing scheduled maintenance. Please check back shortly.",
                "business_name": sys_settings.business_name,
                "phone_number": sys_settings.phone_number,
            },
            status=503,
        )
