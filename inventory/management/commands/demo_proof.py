from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from costing.services import current_balance
from inventory.models import Location, Product, SKU
from purchasing.models import Supplier
from purchasing.services import receive_stock
from sales.models import Customer, Sale
from sales.services import sell_stock

IDEMPOTENCY_KEY = "demo-proof-v1"


class Command(BaseCommand):
    help = "Narrate the 100-in / 12-out proof scenario end to end."

    def handle(self, *args, **options):
        product, _ = Product.objects.get_or_create(
            name="Frozen Chicken (demo)",
            defaults={"description": "Demo SKU for the proof scenario."},
        )
        sku, _ = SKU.objects.get_or_create(
            code="DEMO-CHICKEN-20KG",
            defaults={
                "product": product,
                "unit_weight_kg": Decimal("20.000"),
                "selling_price": Decimal("25000.00"),
            },
        )
        location, _ = Location.objects.get_or_create(
            code="DEMO-MAIN", defaults={"name": "Demo Freezer"},
        )
        supplier, _ = Supplier.objects.get_or_create(name="Demo Supplier")
        customer, _ = Customer.objects.get_or_create(name="Demo Customer")

        existing = Sale.objects.filter(idempotency_key=IDEMPOTENCY_KEY).first()
        if existing:
            self.stdout.write(self.style.WARNING(
                f"demo already ran — sale #{existing.pk} exists, no new writes"
            ))
            self._print_balance(sku)
            return

        self.stdout.write(self.style.MIGRATE_HEADING("─── RECEIVE 100 @ ₦21,000 ───"))
        receipt = receive_stock(
            supplier=supplier, sku=sku, location=location,
            qty=Decimal("100"), unit_cost=Decimal("21000"),
            expiry_date=date(2026, 12, 31),
        )
        self.stdout.write(f"  receipt #{receipt.pk}")
        self._print_balance(sku)
        assert current_balance(sku).qty == Decimal("100")

        self.stdout.write(self.style.MIGRATE_HEADING("─── SELL 12 ───"))
        sale = sell_stock(
            customer=customer, sku=sku, qty=Decimal("12"),
            idempotency_key=IDEMPOTENCY_KEY,
        )
        self.stdout.write(f"  sale #{sale.pk}, total ₦{sale.total_price}")
        self._print_balance(sku)
        assert current_balance(sku).qty == Decimal("88")

        self.stdout.write(self.style.MIGRATE_HEADING("─── TRACE ───"))
        line = sale.lines.get()
        for alloc in line.allocations.all():
            self.stdout.write(
                f"  consumed {alloc.qty} from batch #{alloc.batch_id} "
                f"(expiry {alloc.batch.expiry_date})"
            )

        self.stdout.write(self.style.SUCCESS(
            "✓ proof holds: 100 in, 12 out, 88 remaining"
        ))

    def _print_balance(self, sku):
        b = current_balance(sku)
        self.stdout.write(f"  balance: {b.qty} @ avg ₦{b.avg_cost}")