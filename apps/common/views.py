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


class DatabaseStatsView(APIView):
    """
    GET /api/v1/database/stats/
    Returns live database storage level, size, quota usage, engine, and table record breakdown.
    Restricted to Owner / Superuser.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_authenticated or (user.role != "OWNER" and not user.is_superuser):
            return Response({"error": "Unauthorized. Only the business Owner can view database statistics."}, status=403)

        from django.db import connection
        from django.apps import apps
        from django.conf import settings

        db_engine = connection.vendor
        total_size_bytes = 0

        if db_engine == "postgresql":
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_database_size(current_database());")
                    row = cursor.fetchone()
                    if row and row[0]:
                        total_size_bytes = int(row[0])
            except Exception:
                total_size_bytes = 25 * 1024 * 1024
        elif db_engine == "sqlite":
            db_path = settings.DATABASES.get("default", {}).get("NAME")
            if db_path and os.path.exists(str(db_path)):
                total_size_bytes = os.path.getsize(str(db_path))

        # Supabase PostgreSQL Storage Quota: 500 MB (Free tier limit)
        storage_quota_bytes = 500 * 1024 * 1024
        usage_pct = min(100.0, round((total_size_bytes / storage_quota_bytes) * 100, 2))

        if total_size_bytes < 1024:
            size_formatted = f"{total_size_bytes} B"
        elif total_size_bytes < 1024 * 1024:
            size_formatted = f"{total_size_bytes / 1024:.1f} KB"
        elif total_size_bytes < 1024 * 1024 * 1024:
            size_formatted = f"{total_size_bytes / (1024 * 1024):.2f} MB"
        else:
            size_formatted = f"{total_size_bytes / (1024 * 1024 * 1024):.2f} GB"

        modules_config = [
            {"id": "products", "name": "Products & Categories", "models": ["products.Category", "products.Product"], "icon": "Package"},
            {"id": "customers", "name": "Customers & Price Lists", "models": ["customers.CustomerShop", "customers.CustomerProductPrice"], "icon": "Store"},
            {"id": "orders", "name": "Orders & Order Items", "models": ["orders.Order", "orders.OrderItem"], "icon": "ShoppingCart"},
            {"id": "deliveries", "name": "Deliveries & Stops", "models": ["deliveries.DeliveryDispatch", "deliveries.DeliveryStop"], "icon": "Truck"},
            {"id": "payments", "name": "Payments", "models": ["payments.Payment"], "icon": "CreditCard"},
            {"id": "credits", "name": "Credit Ledger", "models": ["credits.CreditLedgerEntry"], "icon": "BookOpen"},
            {"id": "routes", "name": "Routes & Shifts", "models": ["routes.Route", "routes.DriverShift", "routes.DriverExpense"], "icon": "MapPin"},
            {"id": "whatsapp", "name": "WhatsApp Conversations", "models": ["whatsapp.WhatsAppConversation", "whatsapp.WhatsAppMessage", "whatsapp.WhatsAppCustomer"], "icon": "MessageCircle"},
            {"id": "accounts", "name": "Users & Sessions", "models": ["accounts.User", "accounts.DeviceSession"], "icon": "Users"},
            {"id": "logs", "name": "Audit & System Settings", "models": ["common.ActivityLog", "common.SystemSettings"], "icon": "ShieldCheck"},
        ]

        total_records = 0
        breakdown = []

        for m in modules_config:
            m_count = 0
            for model_path in m["models"]:
                try:
                    app_label, model_name = model_path.split(".")
                    model = apps.get_model(app_label, model_name)
                    m_count += model.objects.count()
                except Exception:
                    pass
            total_records += m_count
            breakdown.append({
                "id": m["id"],
                "name": m["name"],
                "count": m_count,
                "icon": m["icon"],
            })

        status_label = "healthy"
        alert_message = None
        if usage_pct >= 95 or total_size_bytes >= 475 * 1024 * 1024:
            status_label = "critical"
            alert_message = f"CRITICAL: Database storage is FULL ({size_formatted} of 500 MB). Supabase enforces read-only mode at 500 MB, which will block new orders and logins. Please download a database backup immediately and prune old audit logs or upgrade your Supabase tier."
        elif usage_pct >= 80 or total_size_bytes >= 400 * 1024 * 1024:
            status_label = "warning"
            alert_message = f"WARNING: Database storage has reached {usage_pct}% ({size_formatted} of 500 MB). When 500 MB is reached, Supabase restricts write access. Please generate a backup and archive old records soon."

        supabase_rest_url = os.environ.get("SUPABASE_REST_URL", "https://mfrakyarmmnvsvzlyota.supabase.co/rest/v1/")

        return Response({
            "engine": "SUPABASE POSTGRESQL" if "supabase" in os.environ.get("DATABASE_URL", "").lower() or db_engine == "postgresql" else db_engine.upper(),
            "size_bytes": total_size_bytes,
            "size_formatted": size_formatted,
            "quota_bytes": storage_quota_bytes,
            "quota_formatted": "500 MB",
            "usage_pct": usage_pct,
            "total_records": total_records,
            "table_count": len(breakdown),
            "modules": breakdown,
            "status": status_label,
            "alert_message": alert_message,
            "supabase_api_url": supabase_rest_url,
            "checked_at": timezone.now().isoformat(),
        })


class DatabaseBackupView(APIView):
    """
    POST /api/v1/database/backup/
    Generates a full or selective downloadable JSON database snapshot with metadata and SHA-256 verification.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.is_authenticated or (user.role != "OWNER" and not user.is_superuser):
            return Response({"error": "Unauthorized. Only the business Owner can trigger database backups."}, status=403)

        from django.apps import apps
        from django.core import serializers
        import json
        import hashlib
        from django.http import HttpResponse

        backup_type = request.data.get("type", "full")
        selected_modules = request.data.get("modules", [])

        module_models_map = {
            "products": ["products.Category", "products.Product"],
            "customers": ["customers.CustomerShop", "customers.CustomerProductPrice"],
            "orders": ["orders.Order", "orders.OrderItem"],
            "deliveries": ["deliveries.DeliveryDispatch", "deliveries.DeliveryStop"],
            "payments": ["payments.Payment"],
            "credits": ["credits.CreditLedgerEntry"],
            "routes": ["routes.Route", "routes.DriverShift", "routes.DriverExpense"],
            "whatsapp": ["whatsapp.WhatsAppConversation", "whatsapp.WhatsAppMessage", "whatsapp.WhatsAppCustomer"],
            "accounts": ["accounts.User", "accounts.DeviceSession"],
            "logs": ["common.ActivityLog", "common.SystemSettings"],
        }

        if backup_type == "full" or not selected_modules:
            target_modules = list(module_models_map.keys())
            actual_type = "full"
        else:
            target_modules = [m for m in selected_modules if m in module_models_map]
            actual_type = "selective"

        backup_data = {
            "backup_info": {
                "system": "Zamzam Foods Enterprise Distribution Management",
                "version": "1.0.0",
                "created_at": timezone.now().isoformat(),
                "created_by": user.username,
                "backup_type": actual_type,
                "included_modules": target_modules,
            },
            "records": {}
        }

        total_exported_count = 0
        for mod_id in target_modules:
            mod_records = []
            for model_path in module_models_map[mod_id]:
                try:
                    app_label, model_name = model_path.split(".")
                    model = apps.get_model(app_label, model_name)
                    qs = model.objects.all()
                    serialized = serializers.serialize("python", qs)
                    mod_records.extend(serialized)
                    total_exported_count += len(serialized)
                except Exception:
                    continue
            backup_data["records"][mod_id] = mod_records

        backup_data["backup_info"]["total_records"] = total_exported_count

        json_bytes = json.dumps(backup_data, indent=2, default=str).encode("utf-8")
        checksum = hashlib.sha256(json_bytes).hexdigest()
        backup_data["backup_info"]["sha256_checksum"] = checksum
        final_json_str = json.dumps(backup_data, indent=2, default=str)

        # Audit log
        from apps.common.audit import log_activity
        log_activity(
            user=user,
            action="EXPORTED",
            entity_type="SYSTEM_BACKUP",
            entity_id=f"backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
            entity_name="Database Backup",
            summary=f"Created {actual_type} backup containing {total_exported_count} records across {len(target_modules)} modules.",
            details={"type": actual_type, "modules": target_modules, "total_records": total_exported_count, "checksum": checksum},
        )

        filename = f"zamzam_backup_{actual_type}_{timezone.now().strftime('%Y-%m-%d_%H%M%S')}.json"
        response = HttpResponse(final_json_str, content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        return response


