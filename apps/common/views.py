import os
from django.utils import timezone
from rest_framework import viewsets, permissions, filters
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.common.permissions import IsManagerOrOwner
from .models import ActivityLog
from .serializers import ActivityLogSerializer

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only audit history of critical operational and financial events.
    Strictly restricted to Owner and Manager. Drivers are forbidden access.
    """
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsManagerOrOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["summary", "user_name", "entity_name", "entity_id"]
    ordering_fields = ["timestamp", "action", "entity_type"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated or user.role not in ["OWNER", "MANAGER"]:
            return ActivityLog.objects.none()

        qs = ActivityLog.objects.all().select_related("user")

        # Filters
        date_param = self.request.query_params.get("date")
        if date_param:
            qs = qs.filter(timestamp__date=date_param)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)

        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        action = self.request.query_params.get("action")
        if action:
            qs = qs.filter(action=action)

        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)

        user_role = self.request.query_params.get("role")
        if user_role:
            qs = qs.filter(user_role=user_role)

        user_id = self.request.query_params.get("user")
        if user_id:
            qs = qs.filter(user_id=user_id)

        return qs.order_by("-timestamp")


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    GET /api/health/
    Public health check endpoint used by Koyeb to verify the container is alive.
    Returns minimal status — never exposes secrets or internal state.
    """
    return Response({
        "status": "ok",
        "version": "1.0.0",
        "environment": os.environ.get("DJANGO_ENV", "unknown"),
        "timestamp": timezone.now().isoformat(),
    })


class SystemSettingsView(APIView):
    """
    System & Business settings for Zamzam Foods.
    Manages:
    - Master WhatsApp On/Off toggle
    - Master Self-Order On/Off toggle
    - GST number, Phone number, Email, Address, UPI ID, Invoice footer notes
    - GET: Authenticated management view or public safe view
    - PATCH/PUT: Strictly restricted to System Owner / Admin only.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from .models import SystemSettings
        from .serializers import SystemSettingsSerializer, PublicSystemSettingsSerializer

        settings_obj = SystemSettings.get_settings()
        user = request.user
        if user and user.is_authenticated and (user.role in ["OWNER", "MANAGER"] or user.is_superuser):
            serializer = SystemSettingsSerializer(settings_obj)
        else:
            serializer = PublicSystemSettingsSerializer(settings_obj)
        return Response(serializer.data)

    def patch(self, request):
        from rest_framework.exceptions import PermissionDenied
        from .models import SystemSettings
        from .serializers import SystemSettingsSerializer

        user = request.user
        if not user or not user.is_authenticated or (user.role != "OWNER" and not user.is_superuser):
            raise PermissionDenied("Only the business Owner / Administrator can modify system settings.")

        settings_obj = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated_settings = serializer.save()

        # Audit log
        from apps.common.audit import log_activity
        log_activity(
            user=user,
            action="UPDATED",
            entity_type="SYSTEM_SETTING",
            entity_id=str(updated_settings.id),
            entity_name="System Settings",
            summary=f"Updated system settings: WhatsApp={updated_settings.is_whatsapp_enabled}, SelfOrder={updated_settings.is_self_order_enabled}, GST={updated_settings.gst_number}",
            details=serializer.data,
        )

        return Response(SystemSettingsSerializer(updated_settings).data)

    def put(self, request):
        return self.patch(request)

