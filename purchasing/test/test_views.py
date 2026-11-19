from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from inventory.models import Batch, Location, Product, SKU, StockMovement
from purchasing.models import Receipt, Supplier
from costing.models import SKUBalance

User = get_user_model()


def _make_user(username, group=None):
    user = User.objects.create_user(username=username, password="x")
    if group:
        user.groups.add(Group.objects.get(name=group))
    return user


def _fixtures():
    product = Product.objects.create(name="Frozen Chicken")
    sku = SKU.objects.create(product=product, code="CHICKEN-20KG")
    loc = Location.objects.create(code="MAIN", name="Main")
    supplier = Supplier.objects.create(name="Supplier A")
    return product, sku, loc, supplier


class ReceiveFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        _, cls.sku, cls.loc, cls.supplier = _fixtures()
        cls.manager = _make_user("mgr", group="Manager")
        cls.staff = _make_user("stf", group="Inventory Staff")

    def setUp(self):
        self.client.force_login(self.manager)

    def test_manager_can_view_receive_form(self):
        response = self.client.get(reverse("purchasing:receive"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Record a Delivery")

    def test_staff_can_view_receive_form(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("purchasing:receive"))
        self.assertEqual(response.status_code, 200)

    def test_valid_post_creates_records_and_attributes_user(self):
        data = {
            "supplier": self.supplier.pk,
            "sku": self.sku.pk,
            "location": self.loc.pk,
            "qty": "50",
            "unit_cost": "21000",
            "expiry_date": (date.today() + timedelta(days=365)).isoformat(),
            "reference": "PO-123",
            "form_token": "token123"
        }
        response = self.client.post(reverse("purchasing:receive"), data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Receipt.objects.count(), 1)
        receipt = Receipt.objects.first()
        self.assertEqual(receipt.received_by, self.manager)
        self.assertEqual(receipt.reference, "PO-123")

        self.assertEqual(Batch.objects.count(), 1)
        self.assertEqual(StockMovement.objects.count(), 1)
        self.assertEqual(StockMovement.objects.first().user, self.manager)
        self.assertEqual(SKUBalance.objects.get(sku=self.sku).qty, Decimal("50"))

    def test_past_expiry_date_rejected(self):
        data = {
            "supplier": self.supplier.pk,
            "sku": self.sku.pk,
            "location": self.loc.pk,
            "qty": "10",
            "unit_cost": "100",
            "expiry_date": (date.today() - timedelta(days=1)).isoformat(),
        }
        response = self.client.post(reverse("purchasing:receive"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "expiry_date", "Expiry date cannot be in the past.")
        self.assertEqual(Receipt.objects.count(), 0)

    def test_duplicate_submission_blocked(self):
        data = {
            "supplier": self.supplier.pk,
            "sku": self.sku.pk,
            "location": self.loc.pk,
            "qty": "10",
            "unit_cost": "100",
            "expiry_date": (date.today() + timedelta(days=10)).isoformat(),
            "form_token": "token-dupe"
        }
        # First post
        self.client.post(reverse("purchasing:receive"), data, follow=True)
        self.assertEqual(Receipt.objects.count(), 1)

        # Second post with same token
        response = self.client.post(reverse("purchasing:receive"), data, follow=True)
        self.assertEqual(Receipt.objects.count(), 1)  # Still 1
        messages = list(response.context["messages"])
        self.assertTrue(any("Ignored to prevent duplication" in str(m) for m in messages))