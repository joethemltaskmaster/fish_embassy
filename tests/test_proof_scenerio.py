from datetime import date
from decimal import Decimal

from django.test import TestCase

from audit.models import AuditLog
from costing.services import current_balance
from inventory.models import Location, Product, SKU
from purchasing.models import Supplier
from purchasing.services import receive_stock
from sales.models import Customer, Sale
from sales.services import sell_stock


class ProofScenarioTest(TestCase):
    """
    The plan's canonical narrative:
    Supplier A receives 100 cartons of frozen chicken at ₦21,000,
    Customer 1 buys 12. Result: 88 cartons remain, traceable to the batch.
    """

    def test_100_in_12_out(self):
        product = Product.objects.create(name="Frozen Chicken")
        sku = SKU.objects.create(
            product=product, code="CHICKEN-20KG",
            unit_weight_kg=Decimal("20.000"),
            selling_price=Decimal("25000.00"),
        )
        location = Location.objects.create(code="MAIN", name="Main Freezer")
        supplier = Supplier.objects.create(name="Supplier A")
        customer = Customer.objects.create(name="Customer 1")

        # ── receive 100 @ ₦21,000 ──────────────────────────────────────
        receipt = receive_stock(
            supplier=supplier, sku=sku, location=location,
            qty=Decimal("100"), unit_cost=Decimal("21000"),
            expiry_date=date(2026, 12, 31),
        )
        balance = current_balance(sku)
        self.assertEqual(balance.qty, Decimal("100.000"))
        self.assertEqual(balance.avg_cost, Decimal("21000.00"))

        # ── sell 12 ────────────────────────────────────────────────────
        sale = sell_stock(
            customer=customer, sku=sku, qty=Decimal("12"),
            idempotency_key="proof-1",
        )
        balance = current_balance(sku)
        self.assertEqual(balance.qty, Decimal("88.000"))
        self.assertEqual(balance.avg_cost, Decimal("21000.00"))  # unchanged
        self.assertEqual(sale.total_price, Decimal("300000.00"))  # 12 × 25,000

        # ── trace ──────────────────────────────────────────────────────
        line = sale.lines.get()
        allocation = line.allocations.get()
        self.assertEqual(allocation.qty, Decimal("12.000"))
        self.assertEqual(allocation.batch.receipt_line.receipt.pk, receipt.pk)

        # ── audit trail ────────────────────────────────────────────────
        actions = list(AuditLog.objects.values_list("action", flat=True))
        self.assertIn("receive_stock", actions)
        self.assertIn("sell_stock", actions)