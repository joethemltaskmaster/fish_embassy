from django.db import models

from inventory.models import SKU


class SKUBalance(models.Model):
    """Running quantity and average unit cost per SKU."""
    sku = models.OneToOneField(SKU, on_delete=models.PROTECT, related_name="balance")
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    avg_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "SKU balances"

    def __str__(self):
        return f"{self.sku.code}: {self.qty} @ ₦{self.avg_cost}"