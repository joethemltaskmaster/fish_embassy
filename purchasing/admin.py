from django.contrib import admin

from .models import Receipt, ReceiptLine, Supplier


class ReceiptLineInline(admin.TabularInline):
    model = ReceiptLine
    extra = 0
    readonly_fields = ("batch", "stock_movement")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "phone", "email")


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "received_at", "reference")
    list_filter = ("supplier",)
    search_fields = ("supplier__name", "reference")
    date_hierarchy = "received_at"
    readonly_fields = ("received_at",)
    inlines = [ReceiptLineInline]


@admin.register(ReceiptLine)
class ReceiptLineAdmin(admin.ModelAdmin):
    list_display = ("id", "receipt", "sku", "qty", "unit_cost", "expiry_date", "batch")
    list_filter = ("sku", "location")
    search_fields = ("receipt__supplier__name", "sku__code")
    readonly_fields = ("batch", "stock_movement")