from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from inventory.models import Batch, Location, Product, SKU, StockMovement
from purchasing.models import Supplier
from purchasing.services import receive_stock
from sales.models import Customer, Sale
from costing.models import SKUBalance

User = get_user_model()


def _make_user(username, group=None):
    user = User.objects.create_user(username=username, password="x")
    if group:
        user.groups.add(Group.objects.get(name=group))
    return user


class SalesWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        cls.manager = _make_user("mgr", group="Manager")
        cls.staff = _make_user("stf", group="Inventory Staff")

        cls.product = Product.objects.create(name="Fish")
        cls.sku = SKU.objects.create(product=cls.product, code="FISH-20KG", selling_price=Decimal("25000"))
        cls.sku_zero = SKU.objects.create(product=cls.product, code="FISH-ZERO", selling_price=Decimal("0"))
        cls.loc = Location.objects.create(code="MAIN", name="Main")
        cls.supplier = Supplier.objects.create(name="Supplier A")
        cls.customer = Customer.objects.create(name="Customer 1")

        # Provide stock for FISH-20KG
        receive_stock(
            supplier=cls.supplier, sku=cls.sku, location=cls.loc,
            qty=Decimal("50"), unit_cost=Decimal("21000"),
            expiry_date=date.today() + timedelta(days=10)
        )
        receive_stock(
            supplier=cls.supplier, sku=cls.sku, location=cls.loc,
            qty=Decimal("50"), unit_cost=Decimal("22000"),
            expiry_date=date.today() + timedelta(days=60)
        )

        # Provide stock for FISH-ZERO
        receive_stock(
            supplier=cls.supplier, sku=cls.sku_zero, location=cls.loc,
            qty=Decimal("10"), unit_cost=Decimal("100"),
            expiry_date=date.today() + timedelta(days=10)
        )

    def setUp(self):
        self.client.force_login(self.manager)

    def test_staff_cannot_access_sales(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("sales:index"))
        self.assertEqual(response.status_code, 403)

    def test_manager_can_view_sell_page(self):
        response = self.client.get(reverse("sales:sell"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirm Sale")

    def test_valid_sale_creates_records_and_attributes_user(self):
        data = {
            "customer": self.customer.pk,
            "sku": self.sku.pk,
            "qty": "60",
            "reference": "REC-1",
            "idempotency_key": "idem-1"
        }
        response = self.client.post(reverse("sales:sell"), data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.first()
        self.assertEqual(sale.sold_by, self.manager)
        self.assertEqual(sale.total_price, Decimal("1500000.00"))  # 60 * 25000

        # Check FEFO (should consume 50 from first batch, 10 from second)
        allocations = sale.lines.first().allocations.order_by("batch__expiry_date")
        self.assertEqual(allocations[0].qty, Decimal("50"))
        self.assertEqual(allocations[1].qty, Decimal("10"))

        # Check user attribution on movement
        movements = StockMovement.objects.filter(movement_type=StockMovement.MovementType.SALE)
        self.assertEqual(movements[0].user, self.manager)

    def test_sale_with_zero_selling_price_rejected(self):
        data = {
            "customer": self.customer.pk,
            "sku": self.sku_zero.pk,
            "qty": "5",
            "idempotency_key": "idem-zero"
        }
        response = self.client.post(reverse("sales:sell"), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Sale.objects.count(), 0)

        messages = list(response.context["messages"])
        self.assertTrue(any("valid selling price configured" in str(m) for m in messages))

    def test_insufficient_stock_rejected(self):
        data = {
            "customer": self.customer.pk,
            "sku": self.sku.pk,
            "qty": "200",  # Only 100 exist
            "idempotency_key": "idem-over"
        }
        response = self.client.post(reverse("sales:sell"), data, follow=True)
        self.assertEqual(Sale.objects.count(), 0)
        messages = list(response.context["messages"])
        self.assertTrue(any("Insufficient" in str(m) or "only 100.000 on hand" in str(m) for m in messages))

    def test_fefo_preview_api(self):
        url = reverse("sales:fefo_preview") + f"?sku={self.sku.pk}&qty=60"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["sufficient"])
        self.assertEqual(len(data["allocations"]), 2)
        self.assertEqual(data["allocations"][0]["qty"], "50")
        self.assertEqual(data["allocations"][1]["qty"], "10")

    def test_fefo_preview_insufficient(self):
        url = reverse("sales:fefo_preview") + f"?sku={self.sku.pk}&qty=200"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertFalse(data["sufficient"])
        self.assertEqual(data["shortfall"], "100")