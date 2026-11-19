from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from inventory.models import Product, SKU, Location
from purchasing.models import Supplier
from purchasing.services import receive_stock
from sales.models import Customer
from sales.services import sell_stock
from analytics.metrics import (
    get_sales_summary, get_gross_profit_summary, get_stock_valuation,
    get_expiring_batches, get_low_stock_products, get_top_selling_products
)


class AnalyticsMetricsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(name="Frozen Chicken")
        cls.sku1 = SKU.objects.create(
            product=cls.product, code="CHK-01", selling_price=Decimal("100.00"), reorder_level=Decimal("5")
        )
        cls.sku2 = SKU.objects.create(
            product=cls.product, code="CHK-02", selling_price=Decimal("200.00"), reorder_level=Decimal("20")
        )
        cls.loc = Location.objects.create(code="MAIN", name="Main")
        cls.supplier = Supplier.objects.create(name="Supplier A")
        cls.customer = Customer.objects.create(name="Customer A")

        # 1. Receive Stock
        receive_stock(
            supplier=cls.supplier, sku=cls.sku1, location=cls.loc,
            qty=Decimal("10"), unit_cost=Decimal("50.00"),
            expiry_date=date.today() + timedelta(days=10),  # Expiring soon
            received_at=timezone.now()
        )
        receive_stock(
            supplier=cls.supplier, sku=cls.sku2, location=cls.loc,
            qty=Decimal("30"), unit_cost=Decimal("100.00"),
            expiry_date=date.today() + timedelta(days=100),
            received_at=timezone.now()
        )

        # 2. Make Sales (Use timezone.now() to ensure it maps to today's date)
        sell_stock(
            customer=cls.customer, sku=cls.sku1, qty=Decimal("2"),
            idempotency_key="sale-1", occurred_at=timezone.now()
        )
        sell_stock(
            customer=cls.customer, sku=cls.sku2, qty=Decimal("5"),
            idempotency_key="sale-2", occurred_at=timezone.now()
        )

    def test_sales_summary(self):
        res = get_sales_summary(date.today(), date.today())
        self.assertEqual(res['transaction_count'], 2)
        self.assertEqual(res['revenue'], Decimal("1200.00"))  # 200 + 1000
        self.assertEqual(res['units_sold'], Decimal("7.000"))  # 2 + 5

    def test_gross_profit_summary(self):
        res = get_gross_profit_summary(date.today(), date.today())
        self.assertEqual(res['revenue'], Decimal("1200.00"))
        self.assertEqual(res['cogs'], Decimal("600.00"))  # (2*50) + (5*100)
        self.assertEqual(res['gross_profit'], Decimal("600.00"))  # 1200 - 600
        self.assertEqual(res['gross_margin_percent'], Decimal("50.00"))  # (600/1200)*100

    def test_stock_valuation(self):
        res = get_stock_valuation()
        # Remaining: SKU1=8 @ 50 = 400. SKU2=25 @ 100 = 2500. Total = 2900
        self.assertEqual(res['total_inventory_value'], Decimal("2900.00"))
        self.assertEqual(res['total_units'], Decimal("33.000"))

    def test_expiring_batches(self):
        res = get_expiring_batches(days_ahead=30)
        self.assertEqual(len(res), 1)  # Only SKU1 batch should be here
        self.assertEqual(res[0]['sku_code'], "CHK-01")
        self.assertTrue(res[0]['batch_code'].startswith("BATCH-"))

    def test_low_stock_products(self):
        res = get_low_stock_products()
        # SKU1 has 8 left (reorder 5) -> NOT low.
        # SKU2 has 25 left (reorder 20) -> NOT low.
        self.assertEqual(len(res), 0)

        # Sell 4 more SKU1 to drop it below 5
        sell_stock(
            customer=self.customer, sku=self.sku1, qty=Decimal("4"),
            idempotency_key="sale-3", occurred_at=timezone.now()
        )

        res_after = get_low_stock_products()
        self.assertEqual(len(res_after), 1)
        self.assertEqual(res_after[0]['sku_code'], "CHK-01")
        self.assertEqual(res_after[0]['current_qty'], Decimal("4.000"))
        self.assertEqual(res_after[0]['reorder_level'], Decimal("5.000"))

    def test_top_selling_products(self):
        res = get_top_selling_products(date.today(), date.today())
        # SKU2 generated 1000 revenue, SKU1 generated 200.
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]['sku_code'], "CHK-02")
        self.assertEqual(res[0]['revenue'], Decimal("1000.00"))
        self.assertEqual(res[1]['sku_code'], "CHK-01")
        self.assertEqual(res[1]['revenue'], Decimal("200.00"))