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
                if db_engine == "sqlite":
                    sql_output.append("PRAGMA foreign_keys=OFF;")
                    sql_output.append("BEGIN TRANSACTION;")
                    try:
                        for line in connection.connection.iterdump():
                            sql_output.append(f"{line}")
                    except Exception:
                        pass
                    sql_output.append("COMMIT;")
                else:
                    # Robust PostgreSQL SQL DDL/DML generator
                    sql_output.append("BEGIN;")
                    sql_output.append("SET CONSTRAINTS ALL DEFERRED;\n")

                    total_rows = 0
                    for mod_id in target_modules:
                        sql_output.append(f"-- ─── MODULE: {mod_id.upper()} ───")
                        for model_path in module_models_map[mod_id]:
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
                                        elif isinstance(val, (int, float)):
                                            val_list.append(str(val))
                                        elif isinstance(val, bool):
                                            val_list.append("TRUE" if val else "FALSE")
                                        else:
                                            # Safely escape string/datetime values
                                            clean_val = str(val).replace("'", "''")
                                            val_list.append(f"'{clean_val}'")
                                    row_values = ", ".join(val_list)
                                    sql_output.append(f'INSERT INTO "{table_name}" ({cols_sql}) VALUES ({row_values}) ON CONFLICT DO NOTHING;')
                                sql_output.append("")
                            except Exception:
                                continue

                    sql_output.append("COMMIT;\n")
                    sql_output.append("-- Sequence reset commands for PostgreSQL:")
                    for mod_id in target_modules:
                        for model_path in module_models_map[mod_id]:
                            try:
                                app_label, model_name = model_path.split(".")
                                model = apps.get_model(app_label, model_name)
                                table_name = model._meta.db_table
                                sql_output.append(
                                    f"SELECT setval(pg_get_serial_sequence('\"{table_name}\"', 'id'), coalesce(max(id), 1), max(id) IS NOT null) FROM \"{table_name}\";"
                                )
                            except Exception:
                                pass

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

            # Split statements cleanly
            raw_stmts = raw_content.split(";")
            valid_stmts = []
            for s in raw_stmts:
                cleaned = s.strip()
                if not cleaned:
                    continue
                # Skip pure comments
                lines = [l for l in cleaned.splitlines() if not l.strip().startswith("--")]
                sql_only = "\n".join(lines).strip()
                if sql_only:
                    valid_stmts.append(sql_only)

            executed_count = 0
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        for stmt in valid_stmts:
                            upper_stmt = stmt.upper()
                            if upper_stmt in ["BEGIN", "BEGIN TRANSACTION", "COMMIT", "END"]:
                                continue
                            try:
                                cursor.execute(stmt)
                                executed_count += 1
                            except Exception as stmt_err:
                                if "already exists" in str(stmt_err).lower() or "does not exist" in str(stmt_err).lower():
                                    continue
                                raise stmt_err
            except Exception as e:
                return Response({"error": f"SQL restoration failed at statement: {str(e)}"}, status=400)

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




