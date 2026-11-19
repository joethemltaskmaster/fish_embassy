from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from inventory.models import Batch, Location, Product, SKU
from purchasing.models import Supplier
from purchasing.services import receive_stock
from sales.models import Customer, Sale
from sales.services import sell_stock

User = get_user_model()


class SalesStaffRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())

        # Create Sales Staff users
        cls.staff1 = User.objects.create_user(username="staff1", password="x")
        cls.staff1.groups.add(Group.objects.get(name="Sales Staff"))

        cls.staff2 = User.objects.create_user(username="staff2", password="x")
        cls.staff2.groups.add(Group.objects.get(name="Sales Staff"))

        cls.manager = User.objects.create_user(username="mgr", password="x")
        cls.manager.groups.add(Group.objects.get(name="Manager"))

        # Setup base data
        cls.product = Product.objects.create(name="Fish")
        cls.sku = SKU.objects.create(product=cls.product, code="FISH-20KG", selling_price=Decimal("25000"))
        cls.loc = Location.objects.create(code="MAIN", name="Main")
        cls.supplier = Supplier.objects.create(name="Supplier A")
        cls.customer = Customer.objects.create(name="Customer 1")

        receive_stock(
            supplier=cls.supplier, sku=cls.sku, location=cls.loc,
            qty=Decimal("100"), unit_cost=Decimal("21000"),
            expiry_date=date.today() + timedelta(days=10)
        )

        # Staff 1 makes a sale
        cls.sale1 = sell_stock(
            customer=cls.customer, sku=cls.sku, qty=Decimal("10"),
            idempotency_key="sale-1", sold_by=cls.staff1
        )

        # Staff 2 makes a sale
        cls.sale2 = sell_stock(
            customer=cls.customer, sku=cls.sku, qty=Decimal("20"),
            idempotency_key="sale-2", sold_by=cls.staff2
        )

    def setUp(self):
        self.client.force_login(self.staff1)

    # ── ALLOWED ACTIONS ─────────────────────────────────────────
    def test_can_view_dashboard(self):
        response = self.client.get(reverse("dashboard_index"))
        self.assertEqual(response.status_code, 200)
        # Ensure they can't see valuation (they lack costing.view_costs)
        self.assertNotIn("Stock Valuation", response.content.decode())

    def test_can_view_inventory(self):
        for name in ("inventory:products", "inventory:skus", "inventory:balances", "inventory:batches"):
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_can_record_sale(self):
        self.assertEqual(self.client.get(reverse("sales:sell")).status_code, 200)

    def test_can_view_customers(self):
        self.assertEqual(self.client.get(reverse("sales:customers")).status_code, 200)

    def test_can_create_customer(self):
        response = self.client.post(reverse("sales:customer_create"), {
            "name": "New Buyer", "phone": "123", "email": "test@test.com"
        })
        self.assertEqual(response.status_code, 302)  # Redirects on success
        self.assertTrue(Customer.objects.filter(name="New Buyer").exists())

    # ── RESTRICTED ACTIONS ─────────────────────────────────────
    def test_cannot_access_purchasing(self):
        for name in ("purchasing:index", "purchasing:suppliers", "purchasing:receipts", "purchasing:receive"):
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_cannot_access_reports(self):
        for name in ("reports_index", "reports_valuation", "reports_sales", "reports_audit"):
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)

    def test_cannot_access_administration(self):
        self.assertEqual(self.client.get(reverse("administration_index")).status_code, 403)

    # ── "OWN SALES ONLY" RESTRICTION ───────────────────────────
    def test_sales_staff_can_view_shared_sales_history(self):
        # Staff 1 should see all recorded sales.
        response = self.client.get(reverse("sales:list"))

        self.assertEqual(response.status_code, 200)

        sales_in_context = response.context["rows"]

        self.assertIn(self.sale1, sales_in_context)
        self.assertIn(self.sale2, sales_in_context)

        # Staff 2 should have exactly the same access.
        self.client.force_login(self.staff2)

        response = self.client.get(reverse("sales:list"))

        self.assertEqual(response.status_code, 200)

        sales_in_context = response.context["rows"]

        self.assertIn(self.sale1, sales_in_context)
        self.assertIn(self.sale2, sales_in_context)

    def test_manager_can_see_all_sales(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("sales:list"))
        sales_in_context = response.context["rows"]

        # Manager should see BOTH sales
        self.assertIn(self.sale1, sales_in_context)
        self.assertIn(self.sale2, sales_in_context)