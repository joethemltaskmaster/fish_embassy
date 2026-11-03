from decimal import Decimal

from django.test import TestCase

from costing.services import current_balance, update_average_cost
from inventory.models import Product, SKU


class CurrentBalanceTest(TestCase):
    def test_new_sku_has_zero_balance(self):
        product = Product.objects.create(name="Chicken")
        sku = SKU.objects.create(product=product, code="CHK")
        balance = current_balance(sku)
        self.assertEqual(balance.qty, 0)
        self.assertEqual(balance.avg_cost, 0)


class UpdateAverageCostTest(TestCase):
    def setUp(self):
        product = Product.objects.create(name="Chicken")
        self.sku = SKU.objects.create(product=product, code="CHK")

    def test_first_purchase_sets_avg_to_unit_cost(self):
        balance = update_average_cost(
            sku=self.sku, qty=Decimal("100"), unit_cost=Decimal("21000"),
        )
        self.assertEqual(balance.qty, Decimal("100.000"))
        self.assertEqual(balance.avg_cost, Decimal("21000.00"))

    def test_second_purchase_computes_weighted_average(self):
        update_average_cost(sku=self.sku, qty=Decimal("100"), unit_cost=Decimal("21000"))
        balance = update_average_cost(
            sku=self.sku, qty=Decimal("50"), unit_cost=Decimal("30000"),
        )
        self.assertEqual(balance.qty, Decimal("150.000"))
        # (100*21000 + 50*30000) / 150 = 24_000 exactly
        self.assertEqual(balance.avg_cost, Decimal("24000.00"))