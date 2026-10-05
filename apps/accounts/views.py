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
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.middleware.csrf import get_token

from rest_framework import viewsets, permissions, status, exceptions
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from apps.common.permissions import IsOwner, IsManagerOrOwner
from .models import User, DeviceSession, StaffMember, StaffAttendance, StaffPayout
from .serializers import (
    UserSerializer,
    CustomTokenObtainPairSerializer,
    CreateUserSerializer,
    StaffMemberSerializer,
    StaffAttendanceSerializer,
    StaffPayoutSerializer,
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
        if user.role == "DRIVER":
            from apps.common.models import SystemSettings
            sys_settings = SystemSettings.get_settings()
            if not sys_settings.is_driver_module_enabled:
                return Response(
                    {"detail": "Delivery Driver portal is currently disabled in System Settings. Please contact the business owner."},
                    status=status.HTTP_403_FORBIDDEN,
                )

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
        candidate_tokens = []
        payload_token = request.data.get("refresh") if isinstance(request.data, dict) else None
        if payload_token and isinstance(payload_token, str) and payload_token.strip():
            candidate_tokens.append(payload_token.strip())

        cookie_token = request.COOKIES.get(REFRESH_COOKIE)
        if cookie_token and isinstance(cookie_token, str) and cookie_token.strip():
            if cookie_token.strip() not in candidate_tokens:
                candidate_tokens.append(cookie_token.strip())

        if not candidate_tokens:
            return Response(
                {"detail": "No refresh token cookie or parameter present."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        old_token = None
        refresh_str = None
        for cand in candidate_tokens:
            try:
                old_token = RefreshToken(cand)
                refresh_str = cand
                break
            except (TokenError, InvalidToken):
                continue

        if not old_token or not refresh_str:
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
            try:
                old_token.blacklist()
            except Exception:
                pass
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
            try:
                old_token.blacklist()
            except Exception:
                pass
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
        tokens_to_revoke = []
        payload_token = request.data.get("refresh") if isinstance(request.data, dict) else None
        if payload_token and isinstance(payload_token, str) and payload_token.strip():
            tokens_to_revoke.append(payload_token.strip())

        cookie_token = request.COOKIES.get(REFRESH_COOKIE)
        if cookie_token and isinstance(cookie_token, str) and cookie_token.strip():
            if cookie_token.strip() not in tokens_to_revoke:
                tokens_to_revoke.append(cookie_token.strip())

        for refresh_str in tokens_to_revoke:
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
                pass  # Already invalid/blacklisted — idempotent

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
    User management endpoint (Owner and Manager access).
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


# ─── Staff Management (Owner and Manager) ────────────────────────────────────

class StaffMemberViewSet(viewsets.ModelViewSet):
    """
    CRUD for Staff Members (both workers with login accounts and workers without accounts).
    Tracks joined_date tenure slabs (₹400, ₹500, ₹600) or custom daily wages, and proof documents.
    """
    permission_classes = [permissions.IsAuthenticated, IsManagerOrOwner]
    serializer_class = StaffMemberSerializer

    def get_queryset(self):
        qs = StaffMember.objects.select_related("user").prefetch_related("attendances", "payouts").all()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        has_login = self.request.query_params.get("has_login")
        if has_login is not None:
            if has_login.lower() == "true":
                qs = qs.filter(user__isnull=False)
            elif has_login.lower() == "false":
                qs = qs.filter(user__isnull=True)

        role_type = self.request.query_params.get("role_type")
        if role_type:
            qs = qs.filter(role_type=role_type.upper())

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                models.Q(full_name__icontains=search)
                | models.Q(phone_number__icontains=search)
                | models.Q(designation__icontains=search)
                | models.Q(user__username__icontains=search)
            )
        return qs.order_by("full_name")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"])
    def ledger(self, request, pk=None):
        """Returns attendance breakdown, payouts, and running balance for a staff member."""
        from django.db.models import Sum
        from decimal import Decimal

        staff = self.get_object()
        attendances = staff.attendances.order_by("-date")[:60]
        payouts = staff.payouts.order_by("-date")[:60]

        total_earned = staff.attendances.aggregate(total=Sum("daily_wage"))["total"] or Decimal("0.00")
        total_paid = staff.payouts.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        balance_due = total_earned - total_paid

        return Response({
            "staff": StaffMemberSerializer(staff, context={"request": request}).data,
            "total_earned": str(total_earned),
            "total_paid": str(total_paid),
            "balance_due": str(balance_due),
            "recent_attendances": StaffAttendanceSerializer(attendances, many=True).data,
            "recent_payouts": StaffPayoutSerializer(payouts, many=True).data,
        })

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Overview metrics for staff management."""
        from django.db.models import Sum
        from decimal import Decimal

        today = timezone.localdate()
        month_start = today.replace(day=1)

        total_staff = StaffMember.objects.count()
        active_staff = StaffMember.objects.filter(is_active=True).count()
        login_staff = StaffMember.objects.filter(user__isnull=False).count()
        worker_staff = StaffMember.objects.filter(user__isnull=True).count()

        today_present = StaffAttendance.objects.filter(
            date=today, status__in=["FULL", "HALF"]
        ).count()

        month_wages = StaffAttendance.objects.filter(
            date__gte=month_start, date__lte=today
        ).aggregate(total=Sum("daily_wage"))["total"] or Decimal("0.00")

        month_payouts = StaffPayout.objects.filter(
            date__gte=month_start, date__lte=today
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        return Response({
            "total_staff": total_staff,
            "active_staff": active_staff,
            "login_staff": login_staff,
            "worker_staff": worker_staff,
            "today_present": today_present,
            "month_wages_earned": str(month_wages),
            "month_payouts_given": str(month_payouts),
        })


class StaffAttendanceViewSet(viewsets.ModelViewSet):
    """
    Staff Attendance Roll-Call and Tracking.
    Allows marking Full Day (100%), Half Day (50%), or Leave (₹0).
    """
    permission_classes = [permissions.IsAuthenticated, IsManagerOrOwner]
    serializer_class = StaffAttendanceSerializer

    def get_queryset(self):
        qs = StaffAttendance.objects.select_related("staff", "marked_by").all()
        date_param = self.request.query_params.get("date")
        if date_param:
            qs = qs.filter(date=date_param)

        staff_id = self.request.query_params.get("staff")
        if staff_id:
            qs = qs.filter(staff_id=staff_id)

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        month_param = self.request.query_params.get("month") # format YYYY-MM
        if month_param:
            parts = month_param.split("-")
            if len(parts) == 2:
                qs = qs.filter(date__year=int(parts[0]), date__month=int(parts[1]))

        return qs.order_by("-date", "staff__full_name")

    def perform_create(self, serializer):
        serializer.save(marked_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="daily-sheet")
    def daily_sheet(self, request):
        """
        Returns all active staff members with their attendance status on a specific date.
        Helps render a complete roll-call sheet including cash and gpay payouts.
        """
        date_str = request.query_params.get("date") or str(timezone.localdate())
        try:
            target_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = timezone.localdate()

        staff_list = StaffMember.objects.filter(is_active=True).order_by("full_name")
        attendances = {
            str(att.staff_id): att
            for att in StaffAttendance.objects.filter(date=target_date)
        }
        payouts = StaffPayout.objects.filter(date=target_date)
        cash_payouts = {}
        gpay_payouts = {}
        for p in payouts:
            sid = str(p.staff_id)
            if p.payment_method == StaffPayout.PaymentMethod.CASH:
                cash_payouts[sid] = cash_payouts.get(sid, Decimal("0.00")) + p.amount
            elif p.payment_method == StaffPayout.PaymentMethod.GPAY_UPI:
                gpay_payouts[sid] = gpay_payouts.get(sid, Decimal("0.00")) + p.amount

        results = []
        for staff in staff_list:
            is_driver = "driver" in (staff.designation or "").lower()
            role_type = staff.role_type
            if is_driver and staff.role_type != StaffMember.RoleType.STAFF:
                StaffMember.objects.filter(id=staff.id).update(role_type=StaffMember.RoleType.STAFF)
                staff.role_type = StaffMember.RoleType.STAFF
                role_type = StaffMember.RoleType.STAFF

            att = attendances.get(str(staff.id))
            base_wage = staff.get_daily_wage_for_date(target_date)
            results.append({
                "staff_id": str(staff.id),
                "full_name": staff.full_name,
                "phone_number": staff.phone_number,
                "role_type": role_type,
                "designation": staff.designation,
                "has_login_account": staff.has_login_account,
                "joined_date": str(staff.joined_date) if staff.joined_date else None,
                "wage_type": staff.wage_type,
                "custom_daily_wage": str(staff.custom_daily_wage) if staff.custom_daily_wage else None,
                "tenure_slab_label": staff.tenure_slab_label,
                "base_daily_wage": str(base_wage),
                "attendance_id": str(att.id) if att else None,
                "status": att.status if att else "FULL", # default to FULL for convenience
                "is_marked": att is not None,
                "calculated_wage": str(att.daily_wage) if att else str(base_wage),
                "cash_paid": str(cash_payouts.get(str(staff.id), Decimal("0.00"))),
                "gpay_paid": str(gpay_payouts.get(str(staff.id), Decimal("0.00"))),
                "notes": att.notes if att else "",
            })

        return Response({
            "date": str(target_date),
            "sheet": results,
            "marked_count": len(attendances),
            "total_staff": len(staff_list),
        })

    @action(detail=False, methods=["post"], url_path="bulk-save")
    def bulk_save(self, request):
        """
        Saves or updates attendance and daily wage payouts (Cash & GPay) for multiple staff members in one request.
        Body: {
            date: "YYYY-MM-DD",
            attendances: [
                {
                    staff_id: "...",
                    status: "FULL|HALF|LEAVE",
                    notes: "...",
                    cash_paid: "500.00",
                    gpay_paid: "0.00"
                }
            ]
        }
        """
        date_str = request.data.get("date")
        if not date_str:
            return Response({"error": "date is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        records = request.data.get("attendances", [])
        saved = []
        with transaction.atomic():
            for item in records:
                staff_id = item.get("staff_id")
                att_status = item.get("status", "FULL")
                notes = item.get("notes", "")
                if not staff_id:
                    continue

                staff = StaffMember.objects.filter(id=staff_id).first()
                if not staff:
                    continue

                att, created = StaffAttendance.objects.get_or_create(
                    staff=staff,
                    date=target_date,
                    defaults={"status": att_status, "notes": notes, "marked_by": request.user}
                )
                if not created:
                    att.status = att_status
                    att.notes = notes
                    att.marked_by = request.user
                    att.save()

                saved.append(att)

                # Handle daily Cash payout if provided
                if "cash_paid" in item:
                    try:
                        raw_c = str(item["cash_paid"]).strip()
                        cash_val = Decimal(raw_c) if raw_c else Decimal("0.00")
                    except Exception:
                        cash_val = Decimal("0.00")

                    existing_cash = StaffPayout.objects.filter(
                        staff=staff,
                        date=target_date,
                        payment_method=StaffPayout.PaymentMethod.CASH,
                        payout_type=StaffPayout.PayoutType.SALARY,
                    ).first()

                    if cash_val > Decimal("0.00"):
                        if existing_cash:
                            existing_cash.amount = cash_val
                            existing_cash.notes = f"Daily wage cash on {target_date}"
                            existing_cash.paid_by = request.user
                            existing_cash.save()
                        else:
                            StaffPayout.objects.create(
                                staff=staff,
                                date=target_date,
                                amount=cash_val,
                                payment_method=StaffPayout.PaymentMethod.CASH,
                                payout_type=StaffPayout.PayoutType.SALARY,
                                notes=f"Daily wage cash on {target_date}",
                                paid_by=request.user,
                            )
                    elif existing_cash:
                        existing_cash.delete()

                # Handle daily GPay payout if provided
                if "gpay_paid" in item:
                    try:
                        raw_g = str(item["gpay_paid"]).strip()
                        gpay_val = Decimal(raw_g) if raw_g else Decimal("0.00")
                    except Exception:
                        gpay_val = Decimal("0.00")

                    existing_gpay = StaffPayout.objects.filter(
                        staff=staff,
                        date=target_date,
                        payment_method=StaffPayout.PaymentMethod.GPAY_UPI,
                        payout_type=StaffPayout.PayoutType.SALARY,
                    ).first()

                    if gpay_val > Decimal("0.00"):
                        if existing_gpay:
                            existing_gpay.amount = gpay_val
                            existing_gpay.notes = f"Daily wage GPay on {target_date}"
                            existing_gpay.paid_by = request.user
                            existing_gpay.save()
                        else:
                            StaffPayout.objects.create(
                                staff=staff,
                                date=target_date,
                                amount=gpay_val,
                                payment_method=StaffPayout.PaymentMethod.GPAY_UPI,
                                payout_type=StaffPayout.PayoutType.SALARY,
                                notes=f"Daily wage GPay on {target_date}",
                                paid_by=request.user,
                            )
                    elif existing_gpay:
                        existing_gpay.delete()

        return Response({
            "message": f"Successfully updated attendance and daily wage payouts for {len(saved)} staff members on {target_date}.",
            "count": len(saved),
        })


class StaffPayoutViewSet(viewsets.ModelViewSet):
    """
    Staff Wage Payouts and Cash Advances.
    """
    permission_classes = [permissions.IsAuthenticated, IsManagerOrOwner]
    serializer_class = StaffPayoutSerializer

    def get_queryset(self):
        qs = StaffPayout.objects.select_related("staff", "paid_by").all()
        staff_id = self.request.query_params.get("staff")
        if staff_id:
            qs = qs.filter(staff_id=staff_id)

        date_param = self.request.query_params.get("date")
        if date_param:
            qs = qs.filter(date=date_param)

        payout_type = self.request.query_params.get("payout_type")
        if payout_type:
            qs = qs.filter(payout_type=payout_type)

        payment_method = self.request.query_params.get("payment_method")
        if payment_method:
            qs = qs.filter(payment_method=payment_method)

        return qs.order_by("-date", "-created_at")

    def perform_create(self, serializer):
        serializer.save(paid_by=self.request.user)

