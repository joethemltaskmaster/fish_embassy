from django.contrib import admin

from .models import Customer, Sale, SaleAllocation, SaleLine


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "phone", "email")


class SaleLineInline(admin.TabularInline):
    model = SaleLine
    extra = 0
    readonly_fields = ("sku", "qty", "unit_price", "unit_cost")
    can_delete = False


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "occurred_at", "total_price", "idempotency_key")
    list_filter = ("customer",)
    search_fields = ("customer__name", "idempotency_key", "reference")
    date_hierarchy = "occurred_at"
    readonly_fields = ("occurred_at", "idempotency_key")
    inlines = [SaleLineInline]

    # Append-only
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SaleLine)
class SaleLineAdmin(admin.ModelAdmin):
    list_display = ("id", "sale", "sku", "qty", "unit_price", "unit_cost")
    list_filter = ("sku",)
    readonly_fields = ("sale", "sku", "qty", "unit_price", "unit_cost")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SaleAllocation)
class SaleAllocationAdmin(admin.ModelAdmin):
    list_display = ("id", "sale_line", "batch", "qty")
    list_filter = ("batch__sku",)
    readonly_fields = ("sale_line", "batch", "qty", "stock_movement")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False