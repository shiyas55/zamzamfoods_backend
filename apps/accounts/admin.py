from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, DeviceSession

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "phone_number", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "first_name", "last_name", "email", "phone_number")
    ordering = ("-date_joined",)

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Zamzam Role & Contact", {
            "fields": ("role", "phone_number")
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Zamzam Role & Contact", {
            "fields": ("role", "phone_number")
        }),
    )


@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "device_name", "ip_address", "is_active", "expires_at", "last_used_at")
    list_filter = ("is_active", "user__role")
    search_fields = ("user__username", "device_name", "ip_address")
    ordering = ("-last_used_at",)
    readonly_fields = ("id", "user", "refresh_token_hash", "created_at", "last_used_at")
    actions = ["revoke_selected_sessions"]

    def revoke_selected_sessions(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} session(s) revoked.")
    revoke_selected_sessions.short_description = "Revoke selected sessions"
