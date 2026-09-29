from django.contrib import admin
from .models import CreditTransaction

@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ("customer", "transaction_type", "amount", "balance_after", "reference_order", "reference_payment", "recorded_by", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("customer__name", "reference_order__order_number", "reference_payment__payment_number", "notes")
    readonly_fields = ("customer", "transaction_type", "amount", "balance_after", "reference_order", "reference_payment", "recorded_by", "created_at", "updated_at")

    def has_delete_permission(self, request, obj=None):
        # Credit history is an immutable audit log
        return False
