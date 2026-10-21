from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Product(models.Model):
    """A family of goods, e.g. 'Frozen Chicken'."""
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SKU(models.Model):
    """A sellable unit-variant, e.g. 'Frozen Chicken 20 kg carton'."""
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="skus")
    code = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=200, blank=True)
    unit_weight_kg = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True,
        help_text="Weight of one base unit (e.g. 20.000 for a 20 kg carton).",
    )
    base_unit = models.CharField(max_length=20, default="carton")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.product.name}"


class Location(models.Model):
    """A physical place stock can sit, e.g. 'Freezer A', 'Cold room'."""
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Batch(models.Model):
    """
    A physically received lot. Mutable by design — remaining_qty changes as
    sales consume it. Immutability lives on StockMovement, not here.
    """
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="batches")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="batches")
    received_at = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateField()
    received_qty = models.DecimalField(max_digits=12, decimal_places=3)
    remaining_qty = models.DecimalField(max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["expiry_date", "received_at", "id"]  # FEFO by default
        indexes = [models.Index(fields=["sku", "expiry_date"])]

    def clean(self):
        errors = {}
        if self.remaining_qty is not None and self.remaining_qty < 0:
            errors["remaining_qty"] = "Cannot be negative."
        if (self.received_qty is not None and self.remaining_qty is not None
                and self.remaining_qty > self.received_qty):
            errors["remaining_qty"] = "Cannot exceed received_qty."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (f"Batch {self.pk} {self.sku.code} exp {self.expiry_date} "
                f"({self.remaining_qty}/{self.received_qty})")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class StockMovement(models.Model):
    """
    Append-only ledger of stock changes.

    Two layers guard this:
      1. Model-level — save() on an existing row raises; delete() raises.
      2. DB-level  — BEFORE UPDATE / DELETE trigger (migration 0002).
    Queryset operations (`.update()`, `.delete()`) bypass layer 1 and are
    stopped by layer 2 only. That is why both layers exist.
    """

    class MovementType(models.TextChoices):
        RECEIVE = "RECEIVE", "Receive"
        SALE = "SALE", "Sale"
        ADJUST = "ADJUST", "Adjustment"

    sku = models.ForeignKey(SKU, on_delete=models.PROTECT, related_name="movements")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="movements")
    batch = models.ForeignKey(
        Batch, on_delete=models.PROTECT, null=True, blank=True, related_name="movements",
        help_text="Null for pure adjustments; set for anything tied to a specific lot.",
    )
    movement_type = models.CharField(max_length=10, choices=MovementType.choices)
    qty = models.DecimalField(
        max_digits=12, decimal_places=3,
        help_text="Signed: positive for IN, negative for OUT.",
    )
    unit_cost = models.DecimalField(max_digits=14, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [models.Index(fields=["sku", "-occurred_at"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("StockMovement rows are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("StockMovement rows are append-only.")

    def __str__(self):
        sign = "+" if self.qty >= Decimal("0") else ""
        return f"{self.movement_type} {sign}{self.qty} {self.sku.code} @ {self.occurred_at:%Y-%m-%d %H:%M}"


