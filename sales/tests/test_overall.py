from datetime import date
from decimal import Decimal

from django.test import TestCase

from costing.services import current_balance
from inventory.models import Location, Product, SKU, StockMovement
from purchasing.models import Supplier
from purchasing.services import receive_stock
from sales.models import Customer, Sale
from sales.services import InsufficientStock, sell_stock


class OversellTest(TestCase):
    def setUp(self):
        product = Product.objects.create(name="Frozen Chicken")
        self.sku = SKU.objects.create(product=product, code="CHICKEN-20KG")
        self.location = Location.objects.create(code="MAIN", name="Main Freezer")
        self.supplier = Supplier.objects.create(name="Supplier A")
        self.customer = Customer.objects.create(name="Customer 1")
        receive_stock(
            supplier=self.supplier, sku=self.sku, location=self.location,
            qty=Decimal("10"), unit_cost=Decimal("21000"),
            expiry_date=date(2026, 12, 31),
        )

    def test_sell_above_balance_raises_and_rolls_back(self):
        with self.assertRaises(InsufficientStock):
            sell_stock(
                customer=self.customer, sku=self.sku,
                qty=Decimal("11"), idempotency_key="over-1",
            )
        self.assertEqual(current_balance(self.sku).qty, Decimal("10.000"))
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(
            StockMovement.objects.filter(
                movement_type=StockMovement.MovementType.SALE,
            ).count(),
            0,
        )

    def test_sell_exact_balance_succeeds(self):
        sell_stock(
            customer=self.customer, sku=self.sku,
            qty=Decimal("10"), idempotency_key="over-2",
        )
        self.assertEqual(current_balance(self.sku).qty, Decimal("0.000"))