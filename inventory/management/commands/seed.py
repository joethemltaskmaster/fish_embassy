from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from costing.models import SKUBalance
from inventory.models import Location, Product, SKU
from purchasing.models import Supplier
from purchasing.services import receive_stock


class Command(BaseCommand):
    help = "Seed sample data: Supplier A, Frozen Chicken 20 kg SKU, Location MAIN, opening 100 cartons @ ₦21,000."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-stock", action="store_true",
            help="Create the catalog only, no opening receipt.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        product, _ = Product.objects.get_or_create(
            name="Frozen Fish",
            defaults={"description": "Bulk frozen chicken cartons"},
        )
        sku, _ = SKU.objects.get_or_create(
            code="FISH-20KG",
            defaults={
                "product": product,
                "unit_weight_kg": Decimal("20.000"),
                "base_unit": "carton",
                "description": "20 kg carton",
            },
        )
        location, _ = Location.objects.get_or_create(
            code="MAIN", defaults={"name": "Main Freezer"},
        )
        supplier, _ = Supplier.objects.get_or_create(
            name="Supplier A", defaults={"phone": "+234 800 000 0000"},
        )

        self.stdout.write(
            f"catalog: product={product.pk} sku={sku.pk} "
            f"location={location.pk} supplier={supplier.pk}"
        )

        if opts["skip_stock"]:
            self.stdout.write("--skip-stock set, no opening receipt written")
            return

        existing = SKUBalance.objects.filter(sku=sku).values_list("qty", flat=True).first() or 0
        if existing:
            self.stdout.write(f"sku already has balance {existing}, skipping opening receipt")
            return

        receipt = receive_stock(
            supplier=supplier, sku=sku, location=location,
            qty=Decimal("100"), unit_cost=Decimal("21000"),
            expiry_date=date(2026, 12, 31),
            reference="opening",
        )
        self.stdout.write(self.style.SUCCESS(
            f"opening receipt #{receipt.pk}: 100 cartons @ ₦21,000 (expiry 2026-12-31)"
        ))