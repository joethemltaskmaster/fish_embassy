from datetime import date
from decimal import Decimal

from django.test import TestCase

from costing.services import current_balance
from inventory.models import Batch, Location, Product, SKU, StockMovement
from purchasing.models import Supplier
from purchasing.services import receive_stock
from sales.models import Customer, Sale, SaleAllocation, SaleLine
from sales.services import sell_stock


class SellStockBasicTest(TestCase):
    def setUp(self):
        product = Product.objects.create(name="Frozen Chicken")
        self.sku = SKU.objects.create(
            product=product, code="CHICKEN-20KG",
            selling_price=Decimal("25000.00"),
        )
        self.location = Location.objects.create(code="MAIN", name="Main Freezer")
        self.supplier = Supplier.objects.create(name="Supplier A")
        self.customer = Customer.objects.create(name="Customer 1")
        receive_stock(
            supplier=self.supplier, sku=self.sku, location=self.location,
            qty=Decimal("100"), unit_cost=Decimal("21000"),
            expiry_date=date(2026, 12, 31),
        )

    def _sell(self, qty, key="k1"):
        return sell_stock(
            customer=self.customer, sku=self.sku,
            qty=Decimal(qty), idempotency_key=key,
        )

    def test_single_sale_consumes_batch_and_updates_balance(self):
        self._sell(12)
        balance = current_balance(self.sku)
        self.assertEqual(balance.qty, Decimal("88.000"))
        # Avg cost unchanged under average costing
        self.assertEqual(balance.avg_cost, Decimal("21000.00"))

        batch = Batch.objects.get()
        self.assertEqual(batch.remaining_qty, Decimal("88.000"))

    def test_sale_records_price_and_cost(self):
        sale = self._sell(12)
        self.assertEqual(sale.total_price, Decimal("300000.00"))  # 12 × 25,000
        line = sale.lines.get()
        self.assertEqual(line.qty, Decimal("12.000"))
        self.assertEqual(line.unit_price, Decimal("25000.00"))
        self.assertEqual(line.unit_cost, Decimal("21000.00"))     # COGS basis

    def test_sale_writes_one_allocation_and_one_movement(self):
        sale = self._sell(12)
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(SaleLine.objects.count(), 1)
        self.assertEqual(SaleAllocation.objects.count(), 1)
        sale_movements = StockMovement.objects.filter(
            movement_type=StockMovement.MovementType.SALE,
        )
        self.assertEqual(sale_movements.count(), 1)
        self.assertEqual(sale_movements.get().qty, Decimal("-12.000"))

    def test_sale_is_idempotent_on_same_key(self):
        sale1 = self._sell(12, key="same")
        sale2 = self._sell(12, key="same")
        self.assertEqual(sale1.pk, sale2.pk)
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(current_balance(self.sku).qty, Decimal("88.000"))