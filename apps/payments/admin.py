from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_number", "customer", "amount", "payment_method", "status", "collected_by", "received_at")
    list_filter = ("payment_method", "status", "received_at")
    search_fields = ("payment_number", "customer__name", "reference_number", "collected_by__username")
    readonly_fields = ("created_at", "updated_at")
