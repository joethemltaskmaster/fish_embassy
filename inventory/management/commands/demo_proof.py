# inventory/management/commands/demo_proof.py
from django.core.management.base import BaseCommand

from inventory.models import SKU
from inventory.services import current_balance
from purchasing.services import receive_stock
from sales.services import sell_stock


class Command(BaseCommand):
    help = "Narrate the 100-in / 12-out proof scenario end to end."

    def handle(self, *args, **options):
        sku = SKU.objects.get(code="CHICKEN-20KG")

        self.stdout.write("─── RECEIVE 100 cartons @ ₦21,000 ───")
        receive_stock(sku=sku, qty=100, unit_cost=21000, ...)

        after_receive = current_balance(sku)
        self.stdout.write(f"  balance: {after_receive.qty} cartons "
                          f"@ avg ₦{after_receive.avg_cost}")
        assert after_receive.qty == 100, "expected 100 after receive"

        self.stdout.write("─── SELL 12 cartons ───")
        sale = sell_stock(sku=sku, qty=12, customer=..., idempotency_key="demo-1")

        after_sell = current_balance(sku)
        self.stdout.write(f"  balance: {after_sell.qty} cartons")
        assert after_sell.qty == 88, "expected 88 after sell"

        self.stdout.write(self.style.SUCCESS(
            "  ✓ proof holds: 100 in, 12 out, 88 remaining"
        ))