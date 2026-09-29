"""
Cookie-based JWT Authentication class for Django REST Framework.

Reads the access token from the HttpOnly 'zamzam_access' cookie instead of
the Authorization header, keeping tokens completely out of JavaScript's reach.

Falls back to the Bearer header to preserve backwards compatibility with
any existing tooling (e.g. API docs, Postman, internal scripts).
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

ACCESS_COOKIE = "zamzam_access"


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom authentication backend that reads the JWT access token from an
    HttpOnly cookie named ``zamzam_access``.

    Priority:
      1. Cookie  (production path — cookie is HttpOnly, JS can't read it)
      2. Authorization: Bearer <token>  (fallback for Swagger / Postman)
    """

    def authenticate(self, request):
        # 1. Try cookie first
        raw_token = request.COOKIES.get(ACCESS_COOKIE)

        if raw_token:
            try:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token
            except (InvalidToken, TokenError):
                # Cookie token invalid/expired — fall through to header fallback
                pass

        # 2. Fall back to Authorization header (for dev tooling)
        return super().authenticate(request)


# ── drf-spectacular OpenAPI extension (suppresses W001 schema warnings) ───────
try:
    from drf_spectacular.extensions import OpenApiAuthenticationExtension

    class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
        target_class = "apps.common.authentication.CookieJWTAuthentication"
        name = "cookieAuth"

        def get_security_definition(self, auto_schema):
            return {
                "type": "apiKey",
                "in": "cookie",
                "name": "zamzam_access",
                "description": "HttpOnly JWT access token (set by the /auth/login/ endpoint).",
            }

except ImportError:
    pass  # drf-spectacular not installed — skip silently

