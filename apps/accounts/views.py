"""
Zamzam Foods — Authentication Views
Implements secure HttpOnly cookie-based JWT authentication with:
 - Short-lived access tokens (15 min) stored in HttpOnly cookies
 - Refresh tokens (30 days) stored in HttpOnly cookies
 - Per-device persistent sessions (configurable, default 3 days) for Driver/Manager
 - Automatic token rotation on refresh
 - Secure logout with token revocation and cookie clearing
 - Multi-device support via DeviceSession model
"""

import hashlib
import logging
import os
from typing import Optional

from django.conf import settings
from django.utils import timezone
from django.middleware.csrf import get_token

from rest_framework import viewsets, permissions, status, exceptions
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from apps.common.permissions import IsOwner
from .models import User, DeviceSession
from .serializers import (
    UserSerializer,
    CustomTokenObtainPairSerializer,
    CreateUserSerializer,
)

logger = logging.getLogger(__name__)

# ─── Cookie helpers ───────────────────────────────────────────────────────────

COOKIE_SECURE = getattr(settings, "JWT_COOKIE_SECURE", not settings.DEBUG or os.environ.get("JWT_COOKIE_SECURE", "True").lower() == "true")
COOKIE_SAMESITE = getattr(settings, "JWT_COOKIE_SAMESITE", "None" if not settings.DEBUG else "Lax")
ACCESS_COOKIE = "zamzam_access"
REFRESH_COOKIE = "zamzam_refresh"

ACCESS_LIFETIME_SECONDS = (
    int(os.environ.get("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "15")) * 60
)
REFRESH_LIFETIME_DAYS = int(os.environ.get("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "30"))

# Persistent-login period for Driver / Manager (controls device session expiry)
PERSISTENT_LOGIN_DAYS = int(os.environ.get("PERSISTENT_LOGIN_DAYS", "3"))

# Roles that get a persistent session (not Owner/superuser by default)
PERSISTENT_ROLES = {"DRIVER", "MANAGER"}


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    """Write access and refresh tokens into HttpOnly secure cookies."""
    response.set_cookie(
        ACCESS_COOKIE,
        access,
        max_age=ACCESS_LIFETIME_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=REFRESH_LIFETIME_DAYS * 86400,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Expire both auth cookies immediately across all browsers."""
    response.set_cookie(
        ACCESS_COOKIE,
        "",
        max_age=0,
        expires="Thu, 01 Jan 1970 00:00:00 GMT",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE,
        "",
        max_age=0,
        expires="Thu, 01 Jan 1970 00:00:00 GMT",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    response.delete_cookie(ACCESS_COOKIE, path="/", samesite=COOKIE_SAMESITE)
    response.delete_cookie(REFRESH_COOKIE, path="/", samesite=COOKIE_SAMESITE)



def _hash_token(raw_token: str) -> str:
    """Return SHA-256 hex digest of a token string (safe to store in DB)."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _get_client_ip(request) -> Optional[str]:
    """Extract real client IP from request, honouring X-Forwarded-For."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ─── Login ────────────────────────────────────────────────────────────────────

class CookieLoginView(APIView):
    """
    POST /api/v1/auth/login/
    Authenticates with username + password.
    Issues access and refresh tokens as HttpOnly Secure cookies.
    Returns sanitised user profile JSON (no tokens in body).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, InvalidToken) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        except exceptions.AuthenticationFailed as exc:
            return Response(
                {"detail": "Invalid credentials. Please verify your username and password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = serializer.user
        validated = serializer.validated_data  # contains access + refresh strings

        access_str: str = validated["access"]
        refresh_str: str = validated["refresh"]

        response = Response(
            {
                "detail": "Login successful.",
                "access": access_str,
                "refresh": refresh_str,
                "user": validated["user"],
            },
            status=status.HTTP_200_OK,
        )
        _set_auth_cookies(response, access_str, refresh_str)

        # Ensure CSRF token cookie is set (needed for subsequent mutating requests)
        get_token(request)

        # Register device session for Driver / Manager
        if user.role in PERSISTENT_ROLES:
            expires = timezone.now() + timezone.timedelta(days=PERSISTENT_LOGIN_DAYS)
            DeviceSession.objects.create(
                user=user,
                refresh_token_hash=_hash_token(refresh_str),
                device_name=request.data.get("device_name", ""),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                ip_address=_get_client_ip(request),
                expires_at=expires,
            )

        return response


# ─── Token Refresh ────────────────────────────────────────────────────────────

class CookieTokenRefreshView(APIView):
    """
    POST /api/v1/auth/refresh/
    Reads the refresh token from the HttpOnly cookie.
    Validates it, rotates to a new refresh token, and returns a new access token.
    If the persistent device session has expired, returns 401 so the frontend
    redirects the user to login.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_str = request.COOKIES.get(REFRESH_COOKIE) or request.data.get("refresh")
        if not refresh_str:
            return Response(
                {"detail": "No refresh token cookie or parameter present."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            old_token = RefreshToken(refresh_str)
        except (TokenError, InvalidToken):
            resp = Response(
                {"detail": "Refresh token is invalid or expired."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _clear_auth_cookies(resp)
            return resp

        # Validate device session for Driver / Manager (persistent-login check)
        user_id = old_token.get("user_id")
        token_hash = _hash_token(refresh_str)
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            resp = Response({"detail": "User not found."}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_auth_cookies(resp)
            return resp

        if user.role in PERSISTENT_ROLES:
            session = (
                DeviceSession.objects.filter(
                    user=user,
                    refresh_token_hash=token_hash,
                    is_active=True,
                )
                .first()
            )
            if session and not session.is_valid:
                session.is_active = False
                session.save(update_fields=["is_active"])
                resp = Response(
                    {"detail": "Persistent session has expired. Please log in again."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
                _clear_auth_cookies(resp)
                return resp

            # Rotate refresh token — update device session hash or auto-register if missing
            old_token.blacklist()
            new_refresh = RefreshToken.for_user(user)
            new_access_str = str(new_refresh.access_token)
            new_refresh_str = str(new_refresh)

            if session:
                session.refresh_token_hash = _hash_token(new_refresh_str)
                session.save(update_fields=["refresh_token_hash", "last_used_at"])
            else:
                expires = timezone.now() + timezone.timedelta(days=PERSISTENT_LOGIN_DAYS)
                DeviceSession.objects.create(
                    user=user,
                    refresh_token_hash=_hash_token(new_refresh_str),
                    device_name=request.data.get("device_name", "") or "Auto-registered Device",
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                    ip_address=_get_client_ip(request),
                    expires_at=expires,
                )

        else:
            # Owner / other roles — simple rotation without device session tracking
            old_token.blacklist()
            new_refresh = RefreshToken.for_user(user)
            new_access_str = str(new_refresh.access_token)
            new_refresh_str = str(new_refresh)

        response = Response({
            "detail": "Token refreshed.",
            "access": new_access_str,
            "refresh": new_refresh_str,
        }, status=status.HTTP_200_OK)
        _set_auth_cookies(response, new_access_str, new_refresh_str)
        return response


# ─── Logout ───────────────────────────────────────────────────────────────────

class CookieLogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Revokes/blacklists the refresh token, deactivates the device session,
    and clears both auth cookies. The old refresh token cannot be reused.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_str = request.COOKIES.get(REFRESH_COOKIE) or request.data.get("refresh")

        if refresh_str:
            token_hash = _hash_token(refresh_str)

            # Deactivate device session
            DeviceSession.objects.filter(
                refresh_token_hash=token_hash,
                is_active=True,
            ).update(is_active=False)

            # Blacklist the refresh token so it can't be reused
            try:
                token = RefreshToken(refresh_str)
                token.blacklist()
            except (TokenError, InvalidToken):
                pass  # Already invalid — that's fine

        # Also deactivate any active sessions if user is authenticated via Bearer
        if request.user and request.user.is_authenticated:
            DeviceSession.objects.filter(
                user=request.user,
                is_active=True,
            ).update(is_active=False)

        response = Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)
        _clear_auth_cookies(response)
        return response


# ─── User Profile ─────────────────────────────────────────────────────────────

class UserProfileView(APIView):
    """
    GET /api/v1/auth/me/
    Returns the currently authenticated user's profile.
    Authentication is via the HttpOnly access-token cookie.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


# ─── Active Sessions (my devices) ────────────────────────────────────────────

class MySessionsView(APIView):
    """
    GET  /api/v1/auth/sessions/      — list active device sessions
    DELETE /api/v1/auth/sessions/<id>/ — revoke a specific session
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sessions = DeviceSession.objects.filter(
            user=request.user, is_active=True
        ).values(
            "id", "device_name", "ip_address", "created_at", "last_used_at", "expires_at"
        )
        return Response(list(sessions))

    def delete(self, request, session_id=None):
        if not session_id:
            return Response({"detail": "Session ID required."}, status=status.HTTP_400_BAD_REQUEST)
        updated = DeviceSession.objects.filter(
            id=session_id, user=request.user, is_active=True
        ).update(is_active=False)
        if not updated:
            return Response({"detail": "Session not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"detail": "Session revoked."}, status=status.HTTP_200_OK)


# ─── User Management (Owner only) ────────────────────────────────────────────

class UserViewSet(viewsets.ModelViewSet):
    """
    User management endpoint (Owner only).
    """
    queryset = User.objects.all().order_by("-date_joined")
    permission_classes = [IsOwner]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateUserSerializer
        return UserSerializer

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        user = self.get_object()
        new_password = request.data.get("password")
        if not new_password:
            return Response({"error": "Password is required."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
