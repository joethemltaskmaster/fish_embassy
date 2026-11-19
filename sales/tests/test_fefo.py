from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase

from inventory.models import Batch, Location, Product, SKU
from purchasing.models import Supplier
from purchasing.services import receive_stock
from sales.models import Customer, SaleAllocation
from sales.services import sell_stock


class FEFOSelectionTest(TestCase):
    def setUp(self):
        product = Product.objects.create(name="Frozen Fish")
        self.sku = SKU.objects.create(
            product=product, code="FISH-20KG", selling_price=Decimal("25000")
        )
        self.location = Location.objects.create(code="MAIN", name="Main Freezer")
        self.supplier = Supplier.objects.create(name="Supplier A")
        self.customer = Customer.objects.create(name="Customer 1")

    def _receive(self, qty, unit_cost, expiry):
        return receive_stock(
            supplier=self.supplier, sku=self.sku, location=self.location,
            qty=Decimal(qty), unit_cost=Decimal(unit_cost),
            expiry_date=expiry,
        )

    def test_earliest_expiry_consumed_first(self):
        # Batch A: Expires in 10 days
        self._receive(50, 21000, date.today() + timedelta(days=10))
        # Batch B: Expires in 100 days
        self._receive(50, 22000, date.today() + timedelta(days=100))

        sell_stock(
            customer=self.customer, sku=self.sku,
            qty=Decimal("60"), idempotency_key="fefo-1",
        )

        batches = list(Batch.objects.order_by("expiry_date"))
        self.assertEqual(batches[0].remaining_qty, Decimal("0.000"))    # A fully consumed
        self.assertEqual(batches[1].remaining_qty, Decimal("40.000"))   # B → 40 left

    def test_two_allocations_when_splitting_across_batches(self):
        self._receive(50, 21000, date.today() + timedelta(days=10))
        self._receive(50, 22000, date.today() + timedelta(days=100))

        sale = sell_stock(
            customer=self.customer, sku=self.sku,
            qty=Decimal("60"), idempotency_key="fefo-2",
        )
        allocations = sale.lines.get().allocations.order_by("batch__expiry_date")
        self.assertEqual(allocations.count(), 2)
        self.assertEqual(allocations[0].qty, Decimal("50.000"))  # from batch A
        self.assertEqual(allocations[1].qty, Decimal("10.000"))  # from batch B