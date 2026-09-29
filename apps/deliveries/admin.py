from django.contrib import admin
from .models import Delivery

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("delivery_number", "order", "driver", "route", "status", "delivered_at", "recipient_name")
    list_filter = ("status", "route", "driver")
    search_fields = ("delivery_number", "order__order_number", "order__customer__name", "recipient_name")
    readonly_fields = ("created_at", "updated_at")
