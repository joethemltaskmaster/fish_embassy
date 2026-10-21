from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from audit.models import AuditLog
from costing.services import current_balance
from inventory.models import Batch, Location, Product, SKU, StockMovement
from purchasing.models import Receipt, ReceiptLine, Supplier
from purchasing.services import receive_stock

EXPIRY = date(2026, 12, 31)


class ReceiveStockTest(TestCase):
    def setUp(self):
        product = Product.objects.create(name="Frozen Chicken")
        self.sku = SKU.objects.create(
            product=product, code="CHICKEN-20KG",
            unit_weight_kg=Decimal("20.000"),
        )
        self.location = Location.objects.create(code="MAIN", name="Main Freezer")
        self.supplier = Supplier.objects.create(name="Supplier A")

    def _receive(self, qty, unit_cost):
        return receive_stock(
            supplier=self.supplier, sku=self.sku, location=self.location,
            qty=Decimal(qty), unit_cost=Decimal(unit_cost), expiry_date=EXPIRY,
        )

    def test_receive_100_cartons_at_21000(self):
        """Stage 3 exit test — the plan's named test."""
        self._receive(100, 21000)
        balance = current_balance(self.sku)
        self.assertEqual(balance.qty, Decimal("100.000"))
        self.assertEqual(balance.avg_cost, Decimal("21000.00"))

    def test_receive_twice_uses_weighted_average(self):
        self._receive(100, 21000)
        self._receive(50, 30000)
        balance = current_balance(self.sku)
        self.assertEqual(balance.qty, Decimal("150.000"))
        self.assertEqual(balance.avg_cost, Decimal("24000.00"))

    def test_receive_creates_batch_line_and_movement(self):
        receipt = self._receive(100, 21000)

        self.assertEqual(Receipt.objects.count(), 1)
        self.assertEqual(ReceiptLine.objects.count(), 1)
        self.assertEqual(Batch.objects.count(), 1)
        self.assertEqual(StockMovement.objects.count(), 1)

        line = receipt.lines.get()
        self.assertEqual(line.qty, Decimal("100"))
        self.assertEqual(line.batch.remaining_qty, Decimal("100"))
        self.assertEqual(line.batch.expiry_date, EXPIRY)
        self.assertEqual(
            line.stock_movement.movement_type,
            StockMovement.MovementType.RECEIVE,
        )

    def test_receive_writes_audit_log(self):
        self._receive(100, 21000)
        log = AuditLog.objects.filter(action="receive_stock")
        self.assertEqual(log.count(), 1)
        self.assertIn("CHICKEN-20KG", log.first().target)

    def test_receive_rejects_zero_qty(self):
        with self.assertRaises(ValidationError):
            self._receive(0, 21000)
        self.assertEqual(Receipt.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_receive_rejects_negative_unit_cost(self):
        with self.assertRaises(ValidationError):
            self._receive(10, -100)
        self.assertEqual(Receipt.objects.count(), 0)