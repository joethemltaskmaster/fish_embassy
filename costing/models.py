from django.db import models
from inventory.models import SKU
from django.conf import settings
from django.utils import timezone

class SKUBalance(models.Model):

    sku = models.OneToOneField(
        SKU,
        on_delete=models.PROTECT,
        related_name="balance",
    )

    qty = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default=0,
    )

    avg_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name_plural = "SKU balances"

        permissions = [
            (
                "view_costs",
                "Can view cost, avg_cost, and margin data",
            ),
            (
                "view_reports",
                "Can view reports",
            ),
        ]

    def __str__(self):
        return (
            f"{self.sku.code}: "
            f"{self.qty} @ ₦{self.avg_cost}"
        )


class OperatingExpense(models.Model):
    """Records business expenses that are not directly tied to COGS."""

    class Category(models.TextChoices):
        RENT = "RENT", "Rent"
        UTILITIES = "UTILITIES", "Utilities"
        SALARIES = "SALARIES", "Salaries"
        TRANSPORT = "TRANSPORT", "Transport"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        MARKETING = "MARKETING", "Marketing"
        OTHER = "OTHER", "Other"

    date = models.DateField(default=timezone.now)
    category = models.CharField(max_length=20, choices=Category.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    description = models.CharField(max_length=255)

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.date} - {self.category} - ₦{self.amount}"