from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from costing.models import SKUBalance
from inventory.models import Location, Product, SKU
from purchasing.models import Supplier
from purchasing.services import receive_stock
from sales.models import Customer


class Command(BaseCommand):
    help = (
        "Seed sample data: Supplier A, Frozen Chicken 20 kg SKU, "
        "Location MAIN, opening 100 cartons @ ₦21,000."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-stock",
            action="store_true",
            help="Create the catalog only, no opening receipt.",
        )

        parser.add_argument(
            "--with-demo-users",
            action="store_true",
            help="Create demo Manager and Inventory Staff users "
                 "(password printed to stdout; demo/dev only).",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        product, _ = Product.objects.get_or_create(
            name="Frozen Fish",
            defaults={"description": "Bulk frozen fish cartons"},
        )

        sku, created = SKU.objects.get_or_create(
            code="CHICKEN-20KG",
            defaults={
                "product": product,
                "unit_weight_kg": Decimal("20.000"),
                "base_unit": "carton",
                "description": "20 kg carton",
                "selling_price": Decimal("25000.00"),
            },
        )

        if not created and (
            sku.selling_price is None
            or sku.selling_price == 0
        ):
            sku.selling_price = Decimal("25000.00")
            sku.save(update_fields=["selling_price"])

            self.stdout.write(self.style.WARNING(
                f"backfilled selling_price on {sku.code} to ₦25,000"
            ))

        location, _ = Location.objects.get_or_create(
            code="MAIN",
            defaults={"name": "Main Freezer"},
        )

        supplier, _ = Supplier.objects.get_or_create(
            name="Supplier A",
            defaults={"phone": "+234 800 000 0000"},
        )

        customer, _ = Customer.objects.get_or_create(
            name="Customer 1"
        )

        self.stdout.write(f"customer={customer.pk}")

        self.stdout.write(
            f"catalog: product={product.pk} sku={sku.pk} "
            f"location={location.pk} supplier={supplier.pk}"
        )

        # Optional development-only demo users.
        if opts["with_demo_users"]:
            self._create_demo_users()

        if opts["skip_stock"]:
            self.stdout.write(
                "--skip-stock set, no opening receipt written"
            )
            return

        existing = (
            SKUBalance.objects
            .filter(sku=sku)
            .values_list("qty", flat=True)
            .first() or 0
        )

        if existing:
            self.stdout.write(
                f"sku already has balance {existing}, "
                "skipping opening receipt"
            )
            return

        receipt = receive_stock(
            supplier=supplier,
            sku=sku,
            location=location,
            qty=Decimal("100"),
            unit_cost=Decimal("21000"),
            expiry_date=date(2026, 12, 31),
            reference="opening",
        )

        self.stdout.write(self.style.SUCCESS(
            f"opening receipt #{receipt.pk}: "
            "100 cartons @ ₦21,000 (expiry 2026-12-31)"
        ))

    def _create_demo_users(self):
        """Dev-only demo users. Prints password so the operator can sign in."""

        User = get_user_model()
        password = "demo-pass-change-me"

        try:
            manager_group = Group.objects.get(name="Manager")
            staff_group = Group.objects.get(name="Inventory Staff")

        except Group.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "Groups not found. Run "
                "'python manage.py setup_roles' first."
            ))
            return

        for username, group in (
            ("manager_demo", manager_group),
            ("staff_demo", staff_group),
        ):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "is_staff": False,
                    "is_superuser": False,
                },
            )

            if created:
                user.set_password(password)
                user.save()
                user.groups.add(group)

                self.stdout.write(self.style.SUCCESS(
                    f"created user '{username}' "
                    f"in group '{group.name}'"
                ))

            else:
                self.stdout.write(self.style.WARNING(
                    f"user '{username}' already exists; skipping"
                ))

        self.stdout.write(self.style.WARNING(
            f"demo password for both accounts: {password} "
            "(CHANGE BEFORE USE)"
        ))
