from django.contrib import admin
from .models import Customer, CustomerProductPrice

class CustomerProductPriceInline(admin.TabularInline):
    model = CustomerProductPrice
    extra = 0
    fields = ("product", "price", "is_active", "effective_from", "effective_to")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "owner_name", "phone", "route", "current_balance", "credit_limit", "is_active")
    list_filter = ("route", "is_active")
    search_fields = ("name", "owner_name", "phone", "address", "landmark")
    readonly_fields = ("current_balance", "created_at", "updated_at")
    inlines = [CustomerProductPriceInline]


@admin.register(CustomerProductPrice)
class CustomerProductPriceAdmin(admin.ModelAdmin):
    list_display = ("customer", "product", "price", "is_active", "effective_from", "effective_to", "created_at")
    list_filter = ("is_active", "product", "effective_from")
    search_fields = ("customer__name", "product__name", "product__code")
    readonly_fields = ("created_at", "updated_at")
