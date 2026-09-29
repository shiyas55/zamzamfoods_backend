from django.contrib import admin
from .models import Route, Driver, DriverExpense

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("get_driver_name", "assigned_route", "vehicle_number", "phone_number", "is_active")
    list_filter = ("is_active", "assigned_route")
    search_fields = ("user__username", "user__first_name", "user__last_name", "vehicle_number", "phone_number")
    readonly_fields = ("created_at", "updated_at")

    def get_driver_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    get_driver_name.short_description = "Driver"


@admin.register(DriverExpense)
class DriverExpenseAdmin(admin.ModelAdmin):
    list_display = ("driver", "category", "amount", "date", "receipt_reference", "created_at")
    list_filter = ("category", "date", "driver__assigned_route")
    search_fields = ("driver__user__username", "notes", "receipt_reference")
    readonly_fields = ("created_at", "updated_at")
