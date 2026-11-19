from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from inventory.models import Product, SKU, Location
from purchasing.models import Supplier
from sales.models import Customer

User = get_user_model()


class RecordManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())

        cls.superuser = User.objects.create_superuser(username="super", password="x")
        cls.manager = User.objects.create_user(username="mgr", password="x")
        cls.manager.groups.add(Group.objects.get(name="Manager"))

        cls.staff = User.objects.create_user(username="stf", password="x")
        cls.staff.groups.add(Group.objects.get(name="Inventory Staff"))

        cls.sales = User.objects.create_user(username="sls", password="x")
        cls.sales.groups.add(Group.objects.get(name="Sales Staff"))

        # Base objects for ForeignKeys
        cls.product = Product.objects.create(name="Base Chicken")
        cls.loc = Location.objects.create(code="BASE", name="Base Loc")
        cls.supplier = Supplier.objects.create(name="Base Supplier")

    def _login(self, user):
        self.client.force_login(user)

    # ─── MANAGER TESTS ───
    def test_manager_can_create_products(self):
        self._login(self.manager)
        response = self.client.post(reverse("inventory:product_create"), {
            "name": "New Fish", "description": "Test", "is_active": True
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Product.objects.filter(name="New Fish").exists())
        self.assertEqual(Product.objects.get(name="New Fish").created_by, self.manager)

    def test_manager_can_create_supplier(self):
        self._login(self.manager)
        response = self.client.post(reverse("purchasing:supplier_create"), {
            "name": "New Supplier", "is_active": True
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Supplier.objects.filter(name="New Supplier").exists())
        self.assertEqual(Supplier.objects.get(name="New Supplier").created_by, self.manager)

    # ─── INVENTORY STAFF TESTS ───
    def test_inventory_staff_can_create_supplier(self):
        self._login(self.staff)
        response = self.client.post(reverse("purchasing:supplier_create"), {
            "name": "Staff Supplier", "is_active": True
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Supplier.objects.filter(name="Staff Supplier").exists())

    def test_inventory_staff_cannot_create_product(self):
        self._login(self.staff)
        response = self.client.get(reverse("inventory:product_create"))
        self.assertEqual(response.status_code, 403)  # Forbidden

        response = self.client.post(reverse("inventory:product_create"), {
            "name": "Hacked Product", "is_active": True
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Product.objects.filter(name="Hacked Product").exists())

    def test_inventory_staff_cannot_create_sku(self):
        self._login(self.staff)
        response = self.client.get(reverse("inventory:sku_create"))
        self.assertEqual(response.status_code, 403)

    # ─── SALES STAFF TESTS ───
    def test_sales_staff_can_create_customer(self):
        self._login(self.sales)
        response = self.client.post(reverse("sales:customer_create"), {
            "name": "Sales Customer", "phone": "123"
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Customer.objects.filter(name="Sales Customer").exists())

    def test_sales_staff_cannot_create_supplier(self):
        self._login(self.sales)
        response = self.client.get(reverse("purchasing:supplier_create"))
        self.assertEqual(response.status_code, 403)

    def test_sales_staff_cannot_create_product(self):
        self._login(self.sales)
        response = self.client.get(reverse("inventory:product_create"))
        self.assertEqual(response.status_code, 403)