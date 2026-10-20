from django.contrib import admin

from .models import Batch, Location, Product, SKU, StockMovement


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(SKU)
class SKUAdmin(admin.ModelAdmin):
    list_display = ("code", "product", "unit_weight_kg", "base_unit", "is_active")
    list_filter = ("is_active", "base_unit", "product")
    search_fields = ("code", "product__name")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("sku", "location", "expiry_date", "received_qty",
                    "remaining_qty", "unit_cost", "received_at")
    list_filter = ("location", "sku")
    search_fields = ("sku__code", "reference")
    date_hierarchy = "expiry_date"
    readonly_fields = ("created_at",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "movement_type", "sku", "qty", "unit_cost", "reference")
    list_filter = ("movement_type", "sku")
    search_fields = ("sku__code", "reference")
    date_hierarchy = "occurred_at"

    # Append-only: admin may add (Stage 2 debugging), never edit or delete.
    # When services land in Stage 3, flip has_add_permission to False too.
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False