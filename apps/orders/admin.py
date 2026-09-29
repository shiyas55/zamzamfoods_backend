from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("subtotal", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "route", "driver", "order_date", "status", "total_amount", "created_at")
    list_filter = ("status", "route", "order_date")
    search_fields = ("order_number", "customer__name", "driver__user__username")
    readonly_fields = ("total_amount", "created_at", "updated_at")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "unit_price", "subtotal")
    search_fields = ("order__order_number", "product__name")
    readonly_fields = ("subtotal", "created_at", "updated_at")
