from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from inventory.models import Batch, Location, Product, SKU, StockMovement


def _sample_sku():
    product = Product.objects.create(name="Frozen Chicken")
    return SKU.objects.create(product=product, code="CHICKEN-20KG")


def _sample_location():
    return Location.objects.create(code="MAIN", name="Main Freezer")


def _sample_batch(sku, location):
    return Batch.objects.create(
        sku=sku, location=location,
        received_at=timezone.now(),
        expiry_date=date(2026, 12, 31),
        received_qty=Decimal("10"), remaining_qty=Decimal("10"),
        unit_cost=Decimal("21000"),
    )


def _sample_movement(sku, location, qty=Decimal("5")):
    return StockMovement.objects.create(
        sku=sku, location=location,
        movement_type=StockMovement.MovementType.ADJUST,
        qty=qty, unit_cost=Decimal("1"),
    )


class StockMovementAppendOnlyModelTests(TestCase):
    """Model-layer guardrails — no DB trigger needed."""

    def test_create_succeeds(self):
        mv = _sample_movement(_sample_sku(), _sample_location())
        self.assertIsNotNone(mv.pk)

    def test_update_after_create_raises(self):
        mv = _sample_movement(_sample_sku(), _sample_location())
        mv.qty = Decimal("6")
        with self.assertRaises(ValidationError):
            mv.save()

    def test_delete_raises(self):
        mv = _sample_movement(_sample_sku(), _sample_location())
        with self.assertRaises(ValidationError):
            mv.delete()


class StockMovementTriggerTests(TransactionTestCase):
    """DB-layer guardrails — needs real transaction so abort doesn't poison the test."""

    def setUp(self):
        self.sku = _sample_sku()
        self.loc = _sample_location()
        self.mv = _sample_movement(self.sku, self.loc)

    def test_queryset_update_blocked_by_trigger(self):
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                StockMovement.objects.filter(pk=self.mv.pk).update(qty=Decimal("6"))

    def test_queryset_delete_blocked_by_trigger(self):
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                StockMovement.objects.filter(pk=self.mv.pk).delete()

    def test_row_still_present_after_blocked_update(self):
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                StockMovement.objects.filter(pk=self.mv.pk).update(qty=Decimal("999"))
        fresh = StockMovement.objects.get(pk=self.mv.pk)
        self.assertEqual(fresh.qty, Decimal("5"))


class BatchIsMutableTests(TestCase):
    """Prove we did not over-restrict — Batch.remaining_qty must be editable."""

    def test_remaining_qty_can_change(self):
        batch = _sample_batch(_sample_sku(), _sample_location())
        batch.remaining_qty = Decimal("8")
        batch.save()
        batch.refresh_from_db()
        self.assertEqual(batch.remaining_qty, Decimal("8"))

    def test_negative_remaining_qty_rejected(self):
        batch = _sample_batch(_sample_sku(), _sample_location())
        batch.remaining_qty = Decimal("-1")
        with self.assertRaises(ValidationError):
            batch.full_clean()

