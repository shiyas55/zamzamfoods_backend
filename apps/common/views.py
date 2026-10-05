import os
from django.utils import timezone
from rest_framework import viewsets, permissions, filters
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from apps.common.permissions import IsManagerOrOwner
from .models import ActivityLog, BusinessDocument
from .serializers import ActivityLogSerializer, BusinessDocumentSerializer

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


class VerifySettingsPinView(APIView):
    """
    POST /api/v1/settings/verify-pin/
    Verifies if entered 4-digit PIN matches the stored settings_pin_code (Default: 7667).
    Enforces brute-force lockout after 10 consecutive failed attempts per IP.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.core.cache import cache
        from .models import SystemSettings

        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", "unknown")
        cache_key = f"pin_attempts_{ip}"
        failed_attempts = cache.get(cache_key, 0)

        if failed_attempts >= 10:
            return Response(
                {"valid": False, "error": "Too many failed PIN attempts. Please wait 5 minutes before trying again."},
                status=429
            )

        pin = str(request.data.get("pin") or "").strip()
        settings_obj = SystemSettings.get_settings()
        expected_pin = settings_obj.settings_pin_code or "7667"

        if pin == expected_pin:
            cache.delete(cache_key)
            return Response({"valid": True, "message": "PIN verified successfully."})

        cache.set(cache_key, failed_attempts + 1, timeout=300)
        return Response({"valid": False, "error": "Incorrect PIN code. Please try again."}, status=400)


class ResetSettingsPinView(APIView):
    """
    POST /api/v1/settings/reset-pin/
    Resets the 4-digit security PIN by verifying admin (Owner) username and password.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate
        from .models import SystemSettings
        from apps.common.audit import log_activity

        username = str(request.data.get("username") or "").strip()
        password = str(request.data.get("password") or "").strip()
        new_pin = str(request.data.get("new_pin") or "7667").strip()

        if not username or not password:
            return Response({"error": "Admin username and password are required to reset the PIN."}, status=400)

        # Authenticate admin user
        user = authenticate(request, username=username, password=password)
        if not user or not user.is_active or (user.role != "OWNER" and not user.is_superuser):
            return Response({"error": "Invalid admin credentials. Only system Owner / Administrator can reset the PIN."}, status=401)

        if not new_pin.isdigit() or len(new_pin) != 4:
            return Response({"error": "PIN must be exactly 4 numeric digits (e.g. 7667)."}, status=400)

        settings_obj = SystemSettings.get_settings()
        settings_obj.settings_pin_code = new_pin
        settings_obj.save(update_fields=["settings_pin_code", "updated_at"])

        log_activity(
            user=user,
            action="UPDATED",
            entity_type="SYSTEM_SETTING",
            entity_id=str(settings_obj.id),
            entity_name="System Settings",
            summary=f"Security PIN code reset to {new_pin} by admin {user.username}",
            details={"new_pin": new_pin},
        )

        return Response({
            "success": True,
            "message": f"Settings PIN code successfully reset to {new_pin}.",
            "pin": new_pin,
        })


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
            {"id": "accounts", "name": "Users & Staff Profiles", "models": ["accounts.User", "accounts.DeviceSession", "accounts.StaffMember", "accounts.StaffAttendance", "accounts.StaffPayout"], "icon": "Users"},
            {"id": "products", "name": "Products & Pricing", "models": ["products.Product"], "icon": "Package"},
            {"id": "routes", "name": "Routes, Drivers & Shifts", "models": ["routes.Route", "routes.Driver", "routes.DriverShift", "routes.DriverExpense"], "icon": "MapPin"},
            {"id": "customers", "name": "Customer Shops & Documents", "models": ["customers.Customer", "customers.CustomerProductPrice", "customers.CustomerDocument"], "icon": "Store"},
            {"id": "orders", "name": "Orders & Order Items", "models": ["orders.Order", "orders.OrderItem", "orders.OrderActivityLog"], "icon": "ShoppingCart"},
            {"id": "deliveries", "name": "Deliveries & Dispatches", "models": ["deliveries.Delivery"], "icon": "Truck"},
            {"id": "payments", "name": "Payments & Receipts", "models": ["payments.Payment"], "icon": "CreditCard"},
            {"id": "credits", "name": "Credit Ledger Transactions", "models": ["credits.CreditTransaction"], "icon": "BookOpen"},
            {"id": "reports", "name": "Daily Closing Reports", "models": ["reports.DailyClosing"], "icon": "FileText"},
            {"id": "whatsapp", "name": "WhatsApp Messages & Customers", "models": ["whatsapp.WhatsAppAccount", "whatsapp.WhatsAppCustomer", "whatsapp.WhatsAppConversation", "whatsapp.WhatsAppMessage"], "icon": "MessageCircle"},
            {"id": "logs", "name": "Audit & System Settings", "models": ["common.SystemSettings", "common.BusinessDocument", "common.ActivityLog"], "icon": "ShieldCheck"},
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
    Generates a full or selective restorable PostgreSQL SQL or JSON database snapshot with SHA-256 verification.
    Supported formats: 'sql' (default for desktop/pg), 'pg_sql', 'json'.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_authenticated or (user.role not in ["OWNER", "MANAGER"] and not user.is_superuser):
            return Response({"error": "Unauthorized."}, status=403)

        from apps.common.models import ActivityLog
        last_log = ActivityLog.objects.filter(entity_type="SYSTEM_BACKUP").order_by("-created_at").first()

        return Response({
            "supported_formats": ["sql", "json"],
            "default_format": "sql",
            "last_backup": {
                "created_at": last_log.created_at.isoformat() if last_log else None,
                "summary": last_log.summary if last_log else None,
                "details": last_log.details if last_log else {},
                "created_by": last_log.user.username if last_log and last_log.user else None,
            } if last_log else None
        })

    def post(self, request):
        user = request.user
        if not user.is_authenticated or (user.role not in ["OWNER", "MANAGER"] and not user.is_superuser):
            return Response({"error": "Unauthorized. Only Owner or Manager can generate database backups."}, status=403)

        import os
        import json
        import shutil
        import hashlib
        import subprocess
        from django.apps import apps
        from django.db import connection
        from django.core import serializers
        from django.http import HttpResponse

        backup_format = request.data.get("format", "sql").lower()
        backup_type = request.data.get("type", "full")
        selected_modules = request.data.get("modules", [])

        module_models_map = {
            "accounts": ["accounts.User", "accounts.DeviceSession", "accounts.StaffMember", "accounts.StaffAttendance", "accounts.StaffPayout"],
            "products": ["products.Product"],
            "routes": ["routes.Route", "routes.Driver", "routes.DriverShift", "routes.DriverExpense"],
            "customers": ["customers.Customer", "customers.CustomerProductPrice", "customers.CustomerDocument"],
            "orders": ["orders.Order", "orders.OrderItem", "orders.OrderActivityLog"],
            "deliveries": ["deliveries.Delivery"],
            "payments": ["payments.Payment"],
            "credits": ["credits.CreditTransaction"],
            "reports": ["reports.DailyClosing"],
            "whatsapp": ["whatsapp.WhatsAppAccount", "whatsapp.WhatsAppCustomer", "whatsapp.WhatsAppConversation", "whatsapp.WhatsAppMessage"],
            "logs": ["common.SystemSettings", "common.BusinessDocument", "common.ActivityLog"],
        }

        if backup_type == "full" or not selected_modules:
            target_modules = list(module_models_map.keys())
            actual_type = "full"
        else:
            target_modules = [m for m in selected_modules if m in module_models_map]
            actual_type = "selective"

        timestamp_str = timezone.now().strftime("%Y%m%d_%H%M%S")
        db_engine = connection.vendor

        # ── FORMAT 1: RESTORABLE SQL BACKUP ────────────────────────────────────
        if backup_format in ["sql", "pg_sql", "psql"]:
            sql_output = []
            now_iso = timezone.now().isoformat()

            sql_output.append("-- ==============================================================================")
            sql_output.append("-- Zamzam Foods Enterprise Distribution Management")
            sql_output.append(f"-- Database Backup (Format: PostgreSQL Restorable SQL)")
            sql_output.append(f"-- Created At: {now_iso}")
            sql_output.append(f"-- Created By: {user.username}")
            sql_output.append(f"-- Type: {actual_type}")
            sql_output.append("-- ==============================================================================\n")

            # Try native pg_dump if in PostgreSQL environment and pg_dump utility is available
            pg_dump_executed = False
            database_url = os.environ.get("DATABASE_URL", "")

            if db_engine == "postgresql" and shutil.which("pg_dump") and database_url and actual_type == "full":
                try:
                    cmd = ["pg_dump", "--no-owner", "--no-acl", "--clean", "--if-exists", database_url]
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
                    if result.returncode == 0 and result.stdout:
                        sql_content = result.stdout
                        pg_dump_executed = True
                except Exception:
                    pg_dump_executed = False

            if not pg_dump_executed:
                # ── Portable, Universal ORM-based SQL Generator (SQLite & PostgreSQL Compatible) ──
                # We do NOT use sqlite3.iterdump() because it produces SQLite-specific DDL (CREATE TABLE, PRAGMA)
                # that fails when restored to PostgreSQL/Supabase.
                # Instead, we emit pure ANSI/Postgres-compatible INSERT statements with ON CONFLICT DO NOTHING.
                sql_output.append("BEGIN;")
                if db_engine == "postgresql":
                    sql_output.append("SET CONSTRAINTS ALL DEFERRED;\n")
                elif db_engine == "sqlite":
                    sql_output.append("PRAGMA foreign_keys = OFF;\n")

                # Dependency order: parent tables must be inserted before dependent child tables
                ORDERED_MODULES = [
                    "accounts",
                    "products",
                    "routes",
                    "customers",
                    "orders",
                    "deliveries",
                    "payments",
                    "credits",
                    "reports",
                    "whatsapp",
                    "logs",
                ]
                ordered_targets = [m for m in ORDERED_MODULES if m in target_modules]
                for m in target_modules:
                    if m not in ordered_targets:
                        ordered_targets.append(m)

                total_rows = 0
                from django.db.models import JSONField
                import json as _json
                import ast as _ast

                for mod_id in ordered_targets:
                    sql_output.append(f"-- ─── MODULE: {mod_id.upper()} ───")
                    for model_path in module_models_map.get(mod_id, []):
                        try:
                            app_label, model_name = model_path.split(".")
                            model = apps.get_model(app_label, model_name)
                            table_name = model._meta.db_table
                            qs = model.objects.all()
                            count = qs.count()
                            if count == 0:
                                continue

                            total_rows += count
                            sql_output.append(f"-- Table: {table_name} ({count} rows)")

                            fields = [f for f in model._meta.fields]
                            field_names = [f.column for f in fields]
                            cols_sql = ", ".join([f'"{name}"' for name in field_names])

                            for obj in qs.iterator(chunk_size=500):
                                val_list = []
                                for f in fields:
                                    val = getattr(obj, f.attname)
                                    if val is None:
                                        val_list.append("NULL")
                                    elif isinstance(val, bool):
                                        val_list.append("TRUE" if val else "FALSE")
                                    elif isinstance(val, (int, float)):
                                        val_list.append(str(val))
                                    elif isinstance(f, JSONField) or isinstance(val, (dict, list)) or f.name in ["details", "extra", "metadata"]:
                                        # Clean double-quoted JSON string for PostgreSQL & SQLite JSONField
                                        if isinstance(val, (dict, list)):
                                            parsed = val
                                        elif isinstance(val, str):
                                            val_trimmed = val.strip()
                                            try:
                                                parsed = _json.loads(val_trimmed)
                                            except Exception:
                                                try:
                                                    parsed = _ast.literal_eval(val_trimmed)
                                                except Exception:
                                                    parsed = val
                                        else:
                                            parsed = val
                                        json_str = _json.dumps(parsed, default=str)
                                        escaped = json_str.replace("'", "''")
                                        val_list.append(f"'{escaped}'")
                                    else:
                                        # str, UUID, Decimal, datetime, date, etc.
                                        clean_val = str(val).replace("'", "''")
                                        val_list.append(f"'{clean_val}'")
                                row_values = ", ".join(val_list)
                                sql_output.append(f'INSERT INTO "{table_name}" ({cols_sql}) VALUES ({row_values}) ON CONFLICT DO NOTHING;')

                            sql_output.append("")
                        except Exception:
                            continue

                sql_output.append("COMMIT;\n")
                if db_engine == "postgresql":
                    sql_output.append("-- Sequence reset commands for PostgreSQL:")
                    for mod_id in ordered_targets:
                        for model_path in module_models_map.get(mod_id, []):
                            try:
                                app_label, model_name = model_path.split(".")
                                model = apps.get_model(app_label, model_name)
                                table_name = model._meta.db_table
                                sql_output.append(
                                    f"SELECT setval(pg_get_serial_sequence('\"{table_name}\"', 'id'), coalesce(max(id), 1), max(id) IS NOT null) FROM \"{table_name}\";"
                                )
                            except Exception:
                                pass
                elif db_engine == "sqlite":
                    sql_output.append("PRAGMA foreign_keys = ON;\n")

                sql_content = "\n".join(sql_output)

            sql_bytes = sql_content.encode("utf-8")
            checksum = hashlib.sha256(sql_bytes).hexdigest()

            # Audit log
            from apps.common.audit import log_activity
            log_activity(
                user=user,
                action="EXPORTED",
                entity_type="SYSTEM_BACKUP",
                entity_id=f"backup_sql_{timestamp_str}",
                entity_name="PostgreSQL Database Backup",
                summary=f"Created {actual_type} PostgreSQL restorable SQL backup ({len(sql_bytes)} bytes).",
                details={
                    "format": "sql",
                    "type": actual_type,
                    "engine": db_engine,
                    "checksum": checksum,
                    "size_bytes": len(sql_bytes),
                    "modules": target_modules
                },
            )

            filename = f"zamzam_backup_postgresql_{actual_type}_{timestamp_str}.sql"
            response = HttpResponse(sql_content, content_type="application/sql")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            response["X-Backup-Checksum"] = checksum
            response["X-Backup-Format"] = "postgresql-sql"
            response["X-Backup-Size"] = str(len(sql_bytes))
            response["Access-Control-Expose-Headers"] = "Content-Disposition, X-Backup-Checksum, X-Backup-Format, X-Backup-Size"
            return response

        # ── FORMAT 2: JSON SNAPSHOT ───────────────────────────────────────────
        backup_data = {
            "backup_info": {
                "system": "Zamzam Foods Enterprise Distribution Management",
                "version": "1.0.0",
                "created_at": timezone.now().isoformat(),
                "created_by": user.username,
                "backup_type": actual_type,
                "database_engine": db_engine,
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
            entity_id=f"backup_json_{timestamp_str}",
            entity_name="Database Backup",
            summary=f"Created {actual_type} JSON backup containing {total_exported_count} records across {len(target_modules)} modules.",
            details={"format": "json", "type": actual_type, "modules": target_modules, "total_records": total_exported_count, "checksum": checksum},
        )

        filename = f"zamzam_backup_{actual_type}_{timestamp_str}.json"
        response = HttpResponse(final_json_str, content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["X-Backup-Checksum"] = checksum
        response["X-Backup-Format"] = "json"
        response["Access-Control-Expose-Headers"] = "Content-Disposition, X-Backup-Checksum, X-Backup-Format"
        return response


class DatabaseRestoreView(APIView):
    """
    POST /api/v1/database/restore/
    Imports and restores database state from an uploaded SQL (.sql) or JSON (.json) snapshot.
    Supports transactional atomic restore, verification, and audit logging.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.is_authenticated or (user.role not in ["OWNER", "MANAGER"] and not user.is_superuser):
            return Response(
                {"error": "Unauthorized. Only Owner or Manager can restore database backups."},
                status=403
            )

        uploaded_file = request.FILES.get("file")
        raw_content = None
        filename = "upload"

        if uploaded_file:
            filename = uploaded_file.name
            if uploaded_file.size > 50 * 1024 * 1024:  # 50MB limit
                return Response({"error": "File size exceeds 50MB limit."}, status=400)
            try:
                raw_bytes = uploaded_file.read()
                raw_content = raw_bytes.decode("utf-8", errors="replace")
            except Exception as e:
                return Response({"error": f"Failed to read uploaded file: {str(e)}"}, status=400)
        else:
            raw_content = request.data.get("content") or request.data.get("sql")
            filename = request.data.get("filename", "manual_import")

        if not raw_content:
            return Response({"error": "No file uploaded or content provided for import."}, status=400)

        # Detect format
        format_param = request.data.get("format", "").lower()
        if not format_param:
            if filename.lower().endswith(".json") or raw_content.strip().startswith(("{", "[")):
                format_param = "json"
            else:
                format_param = "sql"

        # ── 1. RESTORE FROM JSON ───────────────────────────────────────────
        if format_param == "json":
            import json
            from django.core import serializers
            from django.db import transaction

            try:
                parsed_json = json.loads(raw_content)
            except Exception as e:
                return Response({"error": f"Invalid JSON format: {str(e)}"}, status=400)

            # Extract objects list
            objects_to_deserialize = []
            if isinstance(parsed_json, dict) and "records" in parsed_json:
                records_dict = parsed_json.get("records", {})
                for mod_key, record_list in records_dict.items():
                    if isinstance(record_list, list):
                        objects_to_deserialize.extend(record_list)
            elif isinstance(parsed_json, list):
                objects_to_deserialize = parsed_json
            elif isinstance(parsed_json, dict) and "data" in parsed_json:
                objects_to_deserialize = parsed_json.get("data", [])
            else:
                return Response({
                    "error": "Unrecognized JSON backup schema. Expected 'records' module object or list of serialized Django entities."
                }, status=400)

            restored_count = 0
            try:
                with transaction.atomic():
                    for deserialized_obj in serializers.deserialize("python", objects_to_deserialize, ignorenonexistent=True):
                        deserialized_obj.save()
                        restored_count += 1
            except Exception as e:
                return Response({"error": f"Failed during JSON entity restoration: {str(e)}"}, status=400)

            from apps.common.audit import log_activity
            log_activity(
                user=user,
                action="IMPORTED",
                entity_type="SYSTEM_RESTORE",
                entity_id=f"restore_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                entity_name="Database JSON Import",
                summary=f"Successfully restored {restored_count} entities from JSON file '{filename}'.",
                details={"filename": filename, "format": "json", "records_restored": restored_count},
            )

            return Response({
                "success": True,
                "message": f"Successfully imported and restored {restored_count} records from '{filename}'.",
                "format": "json",
                "records_restored": restored_count,
                "filename": filename,
                "restored_at": timezone.now().isoformat(),
            })

        # ── 2. RESTORE FROM SQL ────────────────────────────────────────────
        elif format_param in ["sql", "pg_sql", "psql"]:
            from django.db import connection, transaction

            # ── String-aware SQL statement splitter ───────────────────────────
            # A naive .split(";") breaks on semicolons inside string literals
            # (e.g. JSON values like '{"note":"a;b"}').
            # This state machine tracks single-quoted string boundaries.
            def split_sql_statements(sql_text: str):
                stmts = []
                current = []
                in_string = False
                i = 0
                n = len(sql_text)
                while i < n:
                    ch = sql_text[i]
                    if in_string:
                        current.append(ch)
                        if ch == "'":
                            # Check for escaped single-quote ''
                            if i + 1 < n and sql_text[i + 1] == "'":
                                current.append("'")
                                i += 2
                                continue
                            else:
                                in_string = False
                    else:
                        if ch == "'":
                            in_string = True
                            current.append(ch)
                        elif ch == "-" and i + 1 < n and sql_text[i + 1] == "-":
                            # Line comment — skip to end of line
                            while i < n and sql_text[i] != "\n":
                                i += 1
                            i += 1
                            continue
                        elif ch == ";":
                            stmt = "".join(current).strip()
                            if stmt:
                                stmts.append(stmt)
                            current = []
                        else:
                            current.append(ch)
                    i += 1
                # Trailing statement without semicolon
                remaining = "".join(current).strip()
                if remaining:
                    stmts.append(remaining)
                return stmts

            # ── Filter: only keep safe DML statements ────────────────────────
            # Skip: transaction controls, DDL (CREATE/DROP/ALTER), SQLite-specific
            # Only run: INSERT, UPDATE, DELETE, SELECT setval(), SET CONSTRAINTS
            _SKIP_PREFIXES = (
                "BEGIN", "COMMIT", "END", "ROLLBACK",
                "CREATE ", "DROP ", "ALTER ", "TRUNCATE ",
                "PRAGMA ",                   # SQLite-specific
                "SET FOREIGN_KEY",           # MySQL-specific
                "LOCK ", "UNLOCK ",
            )
            _SKIP_EXACT = {"BEGIN", "BEGIN TRANSACTION", "COMMIT", "END", "COMMIT TRANSACTION", "ROLLBACK"}

            def _is_safe_stmt(s: str) -> bool:
                upper = s.strip().upper()
                if upper in _SKIP_EXACT:
                    return False
                for prefix in _SKIP_PREFIXES:
                    if upper.startswith(prefix):
                        return False
                return True

            valid_stmts = [
                s for s in split_sql_statements(raw_content)
                if s and _is_safe_stmt(s)
            ]

            if not valid_stmts:
                return Response({
                    "error": "No restorable INSERT statements found in the uploaded file. "
                             "Make sure you upload a Zamzam Foods SQL backup (not a raw SQLite .sql or pg_dump schema file)."
                }, status=400)

            executed_count = 0
            skipped_count = 0
            try:
                # In SQLite, PRAGMA foreign_keys = OFF must be executed outside/before transaction
                if connection.vendor == "sqlite":
                    try:
                        connection.cursor().execute("PRAGMA foreign_keys = OFF;")
                    except Exception:
                        pass

                with transaction.atomic():
                    with connection.cursor() as cursor:
                        # Defer constraints on PostgreSQL
                        if connection.vendor == "postgresql":
                            try:
                                cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
                            except Exception:
                                pass

                        for stmt in valid_stmts:
                            stmt_upper = stmt.strip().upper()
                            # Skip SQLite PRAGMA commands if restoring to PostgreSQL
                            if connection.vendor == "postgresql" and stmt_upper.startswith("PRAGMA"):
                                skipped_count += 1
                                continue
                            # Skip sequence setval commands if restoring to SQLite
                            if connection.vendor == "sqlite" and "SETVAL(" in stmt_upper:
                                skipped_count += 1
                                continue

                            try:
                                cursor.execute(stmt)
                                executed_count += 1
                            except Exception as stmt_err:
                                err_lower = str(stmt_err).lower()
                                # Auto-repair single-quoted JSON dict syntax if PostgreSQL rejected it
                                if "invalid input syntax for type json" in err_lower:
                                    try:
                                        import re
                                        repaired = re.sub(
                                            r"'(\{.*?\})'",
                                            lambda m: "'" + m.group(1).replace("''", '"') + "'",
                                            stmt,
                                            flags=re.DOTALL
                                        )
                                        cursor.execute(repaired)
                                        executed_count += 1
                                        continue
                                    except Exception:
                                        pass

                                # Skip benign duplicate/already exists errors
                                if any(phrase in err_lower for phrase in [
                                    "already exists",
                                    "does not exist",
                                    "duplicate key",
                                    "relation already exists",
                                    "column already exists",
                                    "unique constraint",
                                    "uniqueviolation",
                                ]):
                                    skipped_count += 1
                                    continue
                                # Show first 300 chars of failing statement
                                short_stmt = stmt[:300] + ("..." if len(stmt) > 300 else "")
                                raise Exception(f"{str(stmt_err)} | Statement: {short_stmt}")

                        # Resync PostgreSQL sequences after bulk insert
                        if connection.vendor == "postgresql":
                            from django.apps import apps
                            for model in apps.get_models():
                                try:
                                    table = model._meta.db_table
                                    cursor.execute(
                                        f"SELECT setval(pg_get_serial_sequence('\"{table}\"', 'id'), coalesce(max(id), 1), max(id) IS NOT null) FROM \"{table}\";"
                                    )
                                except Exception:
                                    pass
            except Exception as e:
                return Response({"error": f"SQL restoration failed: {str(e)}"}, status=400)
            finally:
                if connection.vendor == "sqlite":
                    try:
                        connection.cursor().execute("PRAGMA foreign_keys = ON;")
                    except Exception:
                        pass


            from apps.common.audit import log_activity
            log_activity(
                user=user,
                action="IMPORTED",
                entity_type="SYSTEM_RESTORE",
                entity_id=f"restore_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                entity_name="Database SQL Import",
                summary=f"Successfully executed {executed_count} SQL statements from file '{filename}'.",
                details={"filename": filename, "format": "sql", "statements_executed": executed_count},
            )

            return Response({
                "success": True,
                "message": f"Successfully executed and restored {executed_count} SQL statements from '{filename}'.",
                "format": "sql",
                "statements_executed": executed_count,
                "filename": filename,
                "restored_at": timezone.now().isoformat(),
            })

        else:
            return Response({"error": f"Unsupported format: '{format_param}'. Please upload a .sql or .json file."}, status=400)


class BusinessDocumentViewSet(viewsets.ModelViewSet):
    """
    Full CRUD + multi-file batch upload for Zamzam Foods own business documents.
    (FSSAI food safety license, GST, trade license, HALAL cert, etc.)
    Owner/Manager only for write operations. All authenticated users can read.
    """
    serializer_class = BusinessDocumentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "document_number", "issuing_authority", "notes"]
    ordering_fields = ["created_at", "expiry_date", "title", "document_type"]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy", "batch_upload"]:
            return [IsManagerOrOwner()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return BusinessDocument.objects.none()
        qs = BusinessDocument.objects.all()

        doc_type = self.request.query_params.get("document_type")
        if doc_type:
            qs = qs.filter(document_type=doc_type)

        is_expired = self.request.query_params.get("is_expired")
        today = timezone.localdate()
        from django.db.models import Q
        if is_expired == "true":
            qs = qs.filter(expiry_date__lt=today)
        elif is_expired == "false":
            qs = qs.filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        return qs

    def perform_create(self, serializer):
        f = self.request.FILES.get("file")
        file_name = f.name if f else ""
        file_size = f.size if f else 0
        mime_type = getattr(f, "content_type", "") if f else ""
        title = serializer.validated_data.get("title") or file_name or "Business Document"
        serializer.save(
            title=title,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            uploaded_by=self.request.user,
        )

    from rest_framework.decorators import action
    from rest_framework.response import Response as DRFResponse
    from rest_framework import status as drf_status

    @action(detail=False, methods=["post"], url_path="batch-upload")
    def batch_upload(self, request):
        """
        Upload multiple business compliance files at once.
        POST multipart/form-data:
          - document_type, title, document_number, issuing_authority,
            issue_date, expiry_date, notes, is_active
          - files: one or more files
        """
        from rest_framework.decorators import action
        uploaded_files = request.FILES.getlist("files")
        if not uploaded_files:
            single = request.FILES.get("file")
            if single:
                uploaded_files = [single]
            else:
                return Response({"detail": "No files provided."}, status=400)

        doc_type    = request.data.get("document_type") or BusinessDocument.DocumentType.OTHER
        base_title  = request.data.get("title", "").strip()
        doc_number  = request.data.get("document_number", "").strip()
        authority   = request.data.get("issuing_authority", "").strip()
        issue_date  = request.data.get("issue_date") or None
        expiry_date = request.data.get("expiry_date") or None
        notes       = request.data.get("notes", "").strip()
        is_active   = request.data.get("is_active", "true").lower() != "false"

        created = []
        for idx, f in enumerate(uploaded_files):
            file_title = base_title
            if not file_title:
                file_title = f.name
            elif len(uploaded_files) > 1:
                file_title = f"{base_title} ({idx + 1})"

            doc = BusinessDocument.objects.create(
                title=file_title,
                document_type=doc_type,
                file=f,
                file_name=f.name,
                file_size=f.size,
                mime_type=getattr(f, "content_type", ""),
                document_number=doc_number,
                issuing_authority=authority,
                issue_date=issue_date,
                expiry_date=expiry_date,
                notes=notes,
                is_active=is_active,
                uploaded_by=request.user,
            )
            created.append(doc)

        serializer = self.get_serializer(created, many=True, context={"request": request})
        return Response(serializer.data, status=201)


class DatabaseClearAllView(APIView):
    """
    POST /api/v1/database/clear-all/
    Permanently wipes all business and operational data from the database.
    STRICTLY RESTRICTED TO SYSTEM OWNER / SUPERUSER.
    Preserves ONLY accounts with role='OWNER' or is_superuser=True.
    Requires:
      - PIN verification (against SystemSettings.settings_pin_code or admin password)
      - Confirmation phrase: "CLEAR ALL DATA"
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        # Strict authorization: Only Owner or Superuser can execute clear-all
        if not user.is_authenticated or (user.role != "OWNER" and not user.is_superuser):
            return Response(
                {"error": "Unauthorized. Only Business Owner or System Administrator can clear system data."},
                status=403
            )

        from .models import SystemSettings, ActivityLog, BusinessDocument
        from apps.credits.models import CreditTransaction
        from apps.payments.models import Payment
        from apps.deliveries.models import Delivery
        from apps.orders.models import OrderItem, OrderActivityLog, Order
        from apps.whatsapp.models import WhatsAppMessage, WhatsAppConversation, WhatsAppCustomer, WhatsAppAccount
        from apps.customers.models import CustomerDocument, CustomerProductPrice, Customer
        from apps.products.models import Product
        from apps.routes.models import DriverExpense, DriverShift, Driver, Route
        from apps.reports.models import DailyClosing
        from apps.accounts.models import StaffPayout, StaffAttendance, StaffMember, User, DeviceSession
        from django.contrib.admin.models import LogEntry
        from django.db import transaction, models
        from apps.common.audit import log_activity

        settings_obj = SystemSettings.get_settings()
        pin = str(request.data.get("pin") or "").strip()
        confirmation = str(request.data.get("confirmation") or "").strip()

        # Check PIN
        valid_pin = getattr(settings_obj, "settings_pin_code", "7667")
        if pin != valid_pin and not user.check_password(pin):
            return Response(
                {"error": "Invalid security PIN. Please enter your valid 4-digit Owner PIN code."},
                status=400
            )

        # Check Confirmation text
        if confirmation.upper() != "CLEAR ALL DATA":
            return Response(
                {"error": "Please type 'CLEAR ALL DATA' to confirm this irreversible action."},
                status=400
            )

        deleted_counts = {}
        with transaction.atomic():
            # 1. Financial & Operational transactions
            deleted_counts["credit_transactions"] = CreditTransaction.objects.all().delete()[0]
            deleted_counts["payments"] = Payment.objects.all().delete()[0]
            deleted_counts["deliveries"] = Delivery.objects.all().delete()[0]

            # 2. Orders & Order items
            deleted_counts["order_items"] = OrderItem.objects.all().delete()[0]
            deleted_counts["order_activity_logs"] = OrderActivityLog.objects.all().delete()[0]
            deleted_counts["orders"] = Order.objects.all().delete()[0]

            # 3. Customer documents & custom prices & customers
            deleted_counts["customer_documents"] = CustomerDocument.objects.all().delete()[0]
            deleted_counts["customer_product_prices"] = CustomerProductPrice.objects.all().delete()[0]
            deleted_counts["whatsapp_messages"] = WhatsAppMessage.objects.all().delete()[0]
            deleted_counts["whatsapp_conversations"] = WhatsAppConversation.objects.all().delete()[0]
            deleted_counts["whatsapp_customers"] = WhatsAppCustomer.objects.all().delete()[0]
            deleted_counts["whatsapp_accounts"] = WhatsAppAccount.objects.all().delete()[0]
            deleted_counts["customers"] = Customer.objects.all().delete()[0]

            # 4. Products
            deleted_counts["products"] = Product.objects.all().delete()[0]

            # 5. Routes & Shifts & Drivers
            deleted_counts["driver_expenses"] = DriverExpense.objects.all().delete()[0]
            deleted_counts["driver_shifts"] = DriverShift.objects.all().delete()[0]
            deleted_counts["drivers"] = Driver.objects.all().delete()[0]
            deleted_counts["routes"] = Route.objects.all().delete()[0]

            # 6. Reports & Closings
            deleted_counts["daily_closings"] = DailyClosing.objects.all().delete()[0]

            # 7. Staff & Payouts & Attendance
            deleted_counts["staff_payouts"] = StaffPayout.objects.all().delete()[0]
            deleted_counts["staff_attendances"] = StaffAttendance.objects.all().delete()[0]
            deleted_counts["staff_members"] = StaffMember.objects.all().delete()[0]

            # 8. Business Compliance Documents
            deleted_counts["business_documents"] = BusinessDocument.objects.all().delete()[0]

            # 9. Clean non-admin/non-owner device sessions and users
            DeviceSession.objects.exclude(user__role="OWNER").exclude(user__is_superuser=True).delete()

            non_admin_users = User.objects.exclude(role="OWNER").exclude(is_superuser=True)
            non_admin_count = non_admin_users.count()
            non_admin_users.delete()
            deleted_counts["non_admin_users"] = non_admin_count

            # Kept admin / owner accounts
            admin_users = list(
                User.objects.filter(
                    models.Q(role="OWNER") | models.Q(is_superuser=True)
                ).values_list("username", flat=True)
            )

            # 10. Audit Logs & Admin Log entries
            ActivityLog.objects.all().delete()
            LogEntry.objects.all().delete()

            # Record clear-all event as the first entry in fresh ActivityLog
            log_activity(
                user=user,
                action="DELETED",
                entity_type="SYSTEM_SETTING",
                entity_id="clear_all_data",
                entity_name="Database Master Reset",
                summary=f"Full data clear executed by Owner {user.username}. All business data was removed. Admin/Owner accounts ({', '.join(admin_users)}) were preserved.",
                details={"deleted_counts": deleted_counts, "preserved_users": admin_users},
            )

        total_deleted = sum(deleted_counts.values())

        return Response({
            "success": True,
            "message": f"Successfully cleared all data. {total_deleted} records removed. Only Admin and Owner accounts ({', '.join(admin_users)}) are preserved.",
            "deleted_counts": deleted_counts,
            "total_deleted": total_deleted,
            "preserved_users": admin_users,
            "cleared_at": timezone.now().isoformat(),
        })

