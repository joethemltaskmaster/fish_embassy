from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

from audit.models import AuditLog
from inventory.models import Location, Product, SKU
from purchasing.models import Supplier
from purchasing.services import receive_stock
from sales.models import Customer
from sales.services import sell_stock

User = get_user_model()


class PayloadAttributionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())

        cls.sales_staff = User.objects.create_user(username="sales1", first_name="John", last_name="Doe", password="x")
        cls.sales_staff.groups.add(Group.objects.get(name="Sales Staff"))

        cls.purchasing_staff = User.objects.create_user(username="inv1", first_name="Jane", last_name="Smith",
                                                        password="x")
        cls.purchasing_staff.groups.add(Group.objects.get(name="Inventory Staff"))

        product = Product.objects.create(name="Fish")
        cls.sku = SKU.objects.create(product=product, code="FISH-01", selling_price=Decimal("100"))
        cls.loc = Location.objects.create(code="MAIN", name="Main")
        cls.supplier = Supplier.objects.create(name="Supplier A")
        cls.customer = Customer.objects.create(name="Customer A")

    def test_receive_stock_attribution(self):
        receive_stock(
            supplier=self.supplier, sku=self.sku, location=self.loc,
            qty=Decimal("10"), unit_cost=Decimal("50"),
            expiry_date=date.today() + timedelta(days=10),
            user=self.purchasing_staff
        )

        log = AuditLog.objects.get(action="receive_stock")

        # Check Author
        self.assertEqual(log.payload["author"]["id"], self.purchasing_staff.id)
        self.assertEqual(log.payload["author"]["name"], "Jane Smith")
        self.assertEqual(log.payload["author"]["role"], "Inventory Staff")
        self.assertEqual(log.payload["author"]["type"], "user")

        # Check Orchestrator
        self.assertEqual(log.payload["orchestrated_by"]["service"], "purchasing")
        self.assertEqual(log.payload["orchestrated_by"]["component"], "receipt_service")

    def test_sell_stock_attribution(self):
        # Setup stock first
        receive_stock(
            supplier=self.supplier, sku=self.sku, location=self.loc,
            qty=Decimal("10"), unit_cost=Decimal("50"),
            expiry_date=date.today() + timedelta(days=10),
            user=self.purchasing_staff
        )

        sell_stock(
            customer=self.customer, sku=self.sku, qty=Decimal("2"),
            idempotency_key="test-sale", user=self.sales_staff
        )

        log = AuditLog.objects.get(action="sell_stock")

        # Check Author
        self.assertEqual(log.payload["author"]["id"], self.sales_staff.id)
        self.assertEqual(log.payload["author"]["name"], "John Doe")
        self.assertEqual(log.payload["author"]["role"], "Sales Staff")

        # Check Orchestrator
        self.assertEqual(log.payload["orchestrated_by"]["service"], "sales")
        self.assertEqual(log.payload["orchestrated_by"]["component"], "sale_service")

    def test_system_attribution(self):
        # Services without a user should fallback to System
        receive_stock(
            supplier=self.supplier, sku=self.sku, location=self.loc,
            qty=Decimal("10"), unit_cost=Decimal("50"),
            expiry_date=date.today() + timedelta(days=10),
            user=None
        )

        log = AuditLog.objects.get(action="receive_stock")
        self.assertEqual(log.payload["author"]["name"], "System")
        self.assertEqual(log.payload["author"]["type"], "system")
        self.assertIsNone(log.payload["author"]["id"])

    def test_historical_role_snapshot(self):
        receive_stock(
            supplier=self.supplier, sku=self.sku, location=self.loc,
            qty=Decimal("10"), unit_cost=Decimal("50"),
            expiry_date=date.today() + timedelta(days=10),
            user=self.purchasing_staff
        )

        # Change the user's role AFTER the event
        self.purchasing_staff.groups.clear()
        self.purchasing_staff.groups.add(Group.objects.get(name="Manager"))
        self.purchasing_staff.first_name = "Janet"
        self.purchasing_staff.save()

        log = AuditLog.objects.get(action="receive_stock")

        # The log should still show the old role and name
        self.assertEqual(log.payload["author"]["name"], "Jane Smith")
        self.assertEqual(log.payload["author"]["role"], "Inventory Staff")