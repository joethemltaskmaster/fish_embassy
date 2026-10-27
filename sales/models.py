from decimal import Decimal

from django.db import models
from django.utils import timezone

from inventory.models import Batch, SKU, StockMovement


class Customer(models.Model):
    name = models.CharField(max_length=150, unique=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Sale(models.Model):
    """
    Append-only. A wrong sale is compensated by a new sale, never edited.
    `idempotency_key` is the caller's protection against duplicate posting
    on network retry — same key returns the same Sale, no new rows.
    """
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="sales")
    occurred_at = models.DateTimeField(default=timezone.now)
    idempotency_key = models.CharField(max_length=80, unique=True)
    reference = models.CharField(max_length=100, blank=True)
    total_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]

    def __str__(self):
        return f"Sale {self.pk} · {self.customer.name} · ₦{self.total_price}"


class SaleLine(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="lines")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="sale_lines")
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    unit_cost = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text="SKU average cost at the moment of sale (COGS basis).",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Line {self.pk} · {self.sku.code} × {self.qty} @ ₦{self.unit_price}"


class SaleAllocation(models.Model):
    """
    The trace: which physical Batch(es) supplied this sale line.
    One SaleLine can have multiple allocations (FEFO split across batches).
    """
    sale_line = models.ForeignKey(SaleLine, on_delete=models.CASCADE, related_name="allocations")
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="sale_allocations")
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    stock_movement = models.OneToOneField(
        StockMovement, on_delete=models.PROTECT, related_name="sale_allocation",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Allocation {self.pk} · batch {self.batch_id} × {self.qty}"