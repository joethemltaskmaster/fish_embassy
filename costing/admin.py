from django.contrib import admin

from .models import SKUBalance


@admin.register(SKUBalance)
class SKUBalanceAdmin(admin.ModelAdmin):
    list_display = ("sku", "qty", "avg_cost", "updated_at")
    search_fields = ("sku__code", "sku__product__name")
    readonly_fields = ("updated_at",)