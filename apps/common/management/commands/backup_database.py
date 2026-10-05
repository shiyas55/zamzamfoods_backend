import os
import json
import hashlib
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.apps import apps
from django.core import serializers
from django.conf import settings


class Command(BaseCommand):
    help = "Generates an automated, full database snapshot in JSON or SQL format for Zamzam Foods."

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            type=str,
            default="json",
            choices=["json", "sql"],
            help="Backup output format: 'json' (default) or 'sql'",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Custom absolute or relative output file path.",
        )

    def handle(self, *args, **options):
        backup_format = options["format"].lower()
        custom_output = options["output"].strip()

        timestamp_str = timezone.now().strftime("%Y%m%d_%H%M%S")

        # Setup output path
        if custom_output:
            out_path = os.path.abspath(custom_output)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
        else:
            backups_dir = os.path.join(settings.BASE_DIR, "backups")
            os.makedirs(backups_dir, exist_ok=True)
            ext = "sql" if backup_format == "sql" else "json"
            out_path = os.path.join(backups_dir, f"zamzam_backup_auto_{timestamp_str}.{ext}")

        # Models map in strict dependency order
        ordered_models = [
            "accounts.User",
            "accounts.DeviceSession",
            "accounts.StaffMember",
            "accounts.StaffAttendance",
            "accounts.StaffPayout",
            "products.Product",
            "routes.Route",
            "routes.Driver",
            "routes.DriverShift",
            "routes.DriverExpense",
            "customers.Customer",
            "customers.CustomerProductPrice",
            "customers.CustomerDocument",
            "orders.Order",
            "orders.OrderItem",
            "orders.OrderActivityLog",
            "deliveries.Delivery",
            "payments.Payment",
            "credits.CreditTransaction",
            "reports.DailyClosing",
            "whatsapp.WhatsAppAccount",
            "whatsapp.WhatsAppCustomer",
            "whatsapp.WhatsAppConversation",
            "whatsapp.WhatsAppMessage",
            "common.SystemSettings",
            "common.BusinessDocument",
            "common.ActivityLog",
        ]

        total_entities = 0
        all_objects = []

        for model_str in ordered_models:
            try:
                model_cls = apps.get_model(model_str)
                qs = model_cls.objects.all().order_by("pk")
                count = qs.count()
                total_entities += count
                all_objects.extend(list(qs))
                self.stdout.write(f"  • {model_str}: {count} records")
            except Exception as e:
                self.stderr.write(self.style.WARNING(f"Skipping {model_str}: {e}"))

        if backup_format == "json":
            serialized_data = serializers.serialize("json", all_objects, indent=2)
            content_bytes = serialized_data.encode("utf-8")
        else:
            # SQL ANSI dump
            sql_lines = [
                f"-- Zamzam Foods Database Backup ({timestamp_str})",
                "-- Format: PostgreSQL & SQLite ANSI Compatible",
                "BEGIN;\n",
            ]
            for obj in all_objects:
                table = obj._meta.db_table
                fields = [f.column for f in obj._meta.fields]
                vals = []
                for f in obj._meta.fields:
                    v = getattr(obj, f.attname)
                    if v is None:
                        vals.append("NULL")
                    elif isinstance(v, bool):
                        vals.append("TRUE" if v else "FALSE")
                    elif isinstance(v, (int, float)):
                        vals.append(str(v))
                    else:
                        escaped = str(v).replace("'", "''")
                        vals.append(f"'{escaped}'")
                col_names = ", ".join(f'"{c}"' for c in fields)
                col_vals = ", ".join(vals)
                sql_lines.append(f'INSERT INTO "{table}" ({col_names}) VALUES ({col_vals}) ON CONFLICT DO NOTHING;')

            sql_lines.append("\nCOMMIT;")
            content_bytes = "\n".join(sql_lines).encode("utf-8")

        with open(out_path, "wb") as f:
            f.write(content_bytes)

        checksum = hashlib.sha256(content_bytes).hexdigest()
        file_size_kb = round(len(content_bytes) / 1024, 2)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n Backup complete! Total {total_entities} records written to:\n"
                f"   Path:     {out_path}\n"
                f"   Size:     {file_size_kb} KB\n"
                f"   SHA256:   {checksum}\n"
            )
        )
