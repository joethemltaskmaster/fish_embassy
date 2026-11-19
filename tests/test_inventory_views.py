"""
Phase 4a tests: inventory browsing.

Two invariants to prove here, both about security and correctness:
  1. Cost-bearing fields (selling_price, avg_cost, unit_cost, value) are
     absent from the response body for users without costing.view_costs.
  2. Views and selectors return accurate data — no cost leakage, correct
     filters, correct pagination, correct expiry classification.
"""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from html.parser import HTMLParser

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from costing.models import SKUBalance
from inventory.models import Batch, Location, Product, SKU, StockMovement

User = get_user_model()

class PostFormCollector(HTMLParser):
    """Collect POST form actions from rendered HTML."""

    def __init__(self):
        super().__init__()
        self.actions = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "form":
            attributes = dict(attrs)

            if attributes.get("method", "get").lower() == "post":
                self.actions.append(attributes.get("action", ""))

def _make_user(username, group=None, superuser=False):
    user = User.objects.create_user(username=username, password="x")
    user.is_staff = superuser
    user.is_superuser = superuser
    user.save()
    if group:
        user.groups.add(Group.objects.get(name=group))
    return user


def _seeded_fixtures():
    product = Product.objects.create(name="Frozen Chicken")
    sku = SKU.objects.create(
        product=product, code="CHICKEN-20KG",
        unit_weight_kg=Decimal("20.000"),
        selling_price=Decimal("25000.00"),
    )
    location = Location.objects.create(code="MAIN", name="Main Freezer")
    batch = Batch.objects.create(
        sku=sku, location=location,
        expiry_date=date(2027, 12, 31),
        received_qty=Decimal("10"), remaining_qty=Decimal("10"),
        unit_cost=Decimal("21000.00"),
    )
    SKUBalance.objects.create(sku=sku, qty=Decimal("10"), avg_cost=Decimal("21000.00"))
    return product, sku, location, batch


class AnonymousAccessTests(TestCase):
    urls = [
        "inventory:index",
        "inventory:products",
        "inventory:skus",
        "inventory:balances",
        "inventory:batches",
        "inventory:locations",
        "inventory:movements",
    ]

    def test_anonymous_redirected_to_login(self):
        for name in self.urls:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response["Location"])


class StaffAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        _seeded_fixtures()
        cls.staff = _make_user("staff", group="Inventory Staff")

    def setUp(self):
        self.client.force_login(self.staff)

    def test_all_inventory_pages_render(self):
        for name in (
            "inventory:index", "inventory:products", "inventory:skus",
            "inventory:balances", "inventory:batches",
            "inventory:locations", "inventory:movements",
        ):
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)


    def test_skus_list_hides_selling_price(self):
        body = self.client.get(reverse("inventory:skus")).content.decode()
        self.assertNotIn("25000.00", body)
        self.assertNotIn("₦25,000", body)

    def test_balances_list_hides_cost_and_value(self):
        body = self.client.get(reverse("inventory:balances")).content.decode()
        self.assertNotIn("21000.00", body)
        self.assertNotIn("₦21,000", body)

    def test_batches_list_hides_unit_cost(self):
        body = self.client.get(reverse("inventory:batches")).content.decode()
        self.assertNotIn("21000.00", body)
        self.assertNotIn("₦21,000", body)

    def test_movements_list_hides_unit_cost(self):
        StockMovement.objects.create(
            sku=SKU.objects.get(code="CHICKEN-20KG"),
            location=Location.objects.get(code="MAIN"),
            movement_type=StockMovement.MovementType.RECEIVE,
            qty=Decimal("10"),
            unit_cost=Decimal("21000.00"),
        )
        body = self.client.get(reverse("inventory:movements")).content.decode()
        self.assertNotIn("21000.00", body)
        self.assertNotIn("₦21,000", body)


class ManagerAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        _seeded_fixtures()
        cls.mgr = _make_user("mgr", group="Manager")

    def setUp(self):
        self.client.force_login(self.mgr)

    def test_skus_list_shows_selling_price(self):
        body = self.client.get(reverse("inventory:skus")).content.decode()
        self.assertIn("25,000", body)

    def test_balances_list_shows_avg_cost(self):
        body = self.client.get(reverse("inventory:balances")).content.decode()
        self.assertIn("21,000", body)

    def test_batches_list_shows_unit_cost(self):
        body = self.client.get(reverse("inventory:batches")).content.decode()
        self.assertIn("21,000", body)


class EmptyDatabaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        cls.mgr = _make_user("mgr_empty", group="Manager")

    def setUp(self):
        self.client.force_login(self.mgr)

    def test_all_lists_render_with_empty_db(self):
        for name in (
            "inventory:products", "inventory:skus", "inventory:balances",
            "inventory:batches", "inventory:locations", "inventory:movements",
        ):
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertIn("empty-state", response.content.decode())


class ExpiryClassificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        cls.mgr = _make_user("mgr_exp", group="Manager")
        product = Product.objects.create(name="Chicken")
        cls.sku = SKU.objects.create(product=product, code="CHK")
        cls.loc = Location.objects.create(code="MAIN", name="Main")

        today = date.today()
        cls.expired = Batch.objects.create(
            sku=cls.sku, location=cls.loc,
            expiry_date=today - timedelta(days=1),
            received_qty=Decimal("5"), remaining_qty=Decimal("5"),
            unit_cost=Decimal("1"),
        )
        cls.expiring = Batch.objects.create(
            sku=cls.sku, location=cls.loc,
            expiry_date=today + timedelta(days=10),
            received_qty=Decimal("5"), remaining_qty=Decimal("5"),
            unit_cost=Decimal("1"),
        )
        cls.fresh = Batch.objects.create(
            sku=cls.sku, location=cls.loc,
            expiry_date=today + timedelta(days=180),
            received_qty=Decimal("5"), remaining_qty=Decimal("5"),
            unit_cost=Decimal("1"),
        )

    def setUp(self):
        self.client.force_login(self.mgr)


    def test_expired_filter(self):
        response = self.client.get(
            reverse("inventory:batches") + "?expiry=expired"
        )

        self.assertEqual(response.status_code, 200)

        rows = response.context["rows"]

        self.assertEqual(
            [row["pk"] for row in rows],
            [self.expired.pk],
        )
        self.assertEqual(
            [row["status"] for row in rows],
            ["expired"],
        )

    def test_expiring_filter(self):
        response = self.client.get(
            reverse("inventory:batches") + "?expiry=expiring"
        )

        self.assertEqual(response.status_code, 200)

        rows = response.context["rows"]

        self.assertEqual(
            [row["pk"] for row in rows],
            [self.expiring.pk],
        )
        self.assertEqual(
            [row["status"] for row in rows],
            ["expiring"],
        )

    def test_fresh_filter(self):
        response = self.client.get(
            reverse("inventory:batches") + "?expiry=fresh"
        )

        self.assertEqual(response.status_code, 200)

        rows = response.context["rows"]

        self.assertEqual(
            [row["pk"] for row in rows],
            [self.fresh.pk],
        )
        self.assertEqual(
            [row["status"] for row in rows],
            ["fresh"],
        )



class SearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        cls.mgr = _make_user("mgr_search", group="Manager")
        Product.objects.create(name="Frozen Chicken")
        Product.objects.create(name="Fresh Fish")

    def setUp(self):
        self.client.force_login(self.mgr)

    def test_product_search_matches_name(self):
        body = self.client.get(reverse("inventory:products") + "?q=Fish").content.decode()
        self.assertIn("Fresh Fish", body)
        self.assertNotIn("Frozen Chicken", body)


class PaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        cls.mgr = _make_user("mgr_pg", group="Manager")
        product = Product.objects.create(name="Base")
        for i in range(30):
            SKU.objects.create(product=product, code=f"SKU-{i:03d}")

    def setUp(self):
        self.client.force_login(self.mgr)

    def test_page_1_has_25_items(self):
        body = self.client.get(reverse("inventory:skus")).content.decode()
        self.assertIn("Page 1 of 2", body)
        self.assertIn("30 items", body)

    def test_page_2_exists(self):
        body = self.client.get(reverse("inventory:skus") + "?page=2").content.decode()
        self.assertIn("Page 2 of 2", body)


class MovementsAreReadOnlyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        cls.mgr = _make_user("mgr_mv", group="Manager")
        _seeded_fixtures()
        StockMovement.objects.create(
            sku=SKU.objects.get(code="CHICKEN-20KG"),
            location=Location.objects.get(code="MAIN"),
            movement_type=StockMovement.MovementType.RECEIVE,
            qty=Decimal("10"), unit_cost=Decimal("21000"),
        )

    def setUp(self):
        self.client.force_login(self.mgr)


    def test_no_edit_links_in_movements_page(self):
        response = self.client.get(
            reverse("inventory:movements")
        )

        self.assertEqual(response.status_code, 200)

        body = response.content.decode()

        self.assertNotIn("/edit/", body)
        self.assertNotIn("/delete/", body)

        # The shared layout may contain a logout POST form.
        # No other POST form should appear on the read-only page.
        parser = PostFormCollector()
        parser.feed(body)

        self.assertEqual(
            parser.actions,
            ["/accounts/logout/"],
            f"Unexpected POST forms: {parser.actions}",
        )
