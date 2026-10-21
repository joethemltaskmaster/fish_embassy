from django.db import models
from django.utils import timezone

from inventory.models import Batch, Location, SKU, StockMovement


class Supplier(models.Model):
    name = models.CharField(max_length=150, unique=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Receipt(models.Model):
    """Header for an incoming purchase. One receipt → one or more lines."""
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="receipts")
    received_at = models.DateTimeField(default=timezone.now)
    reference = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at", "-id"]

    def __str__(self):
        return f"Receipt {self.pk} · {self.supplier.name} · {self.received_at:%Y-%m-%d}"


class ReceiptLine(models.Model):
    """
    One SKU-line on a receipt. Links to the physical Batch (FEFO target)
    and the StockMovement (append-only ledger entry) it produced. Those
    FKs are the traceability back-bone — no edits to StockMovement needed.
    """
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name="lines")
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="receipt_lines")
    location = models.ForeignKey(Location, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2)
    expiry_date = models.DateField()

    batch = models.OneToOneField(
        Batch, on_delete=models.PROTECT, related_name="receipt_line",
    )
    stock_movement = models.OneToOneField(
        StockMovement, on_delete=models.PROTECT, related_name="receipt_line",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Line {self.pk} · {self.sku.code} × {self.qty} @ ₦{self.unit_cost}"