from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum
from inventory.models import Batch, StockMovement
from costing.models import SKUBalance
from sales.models import SaleLine, SaleAllocation
from purchasing.models import ReceiptLine

class Command(BaseCommand):
    help = "Reconcile synthetic data to ensure database integrity."

    def handle(self, *args, **options):
        self.stdout.write("Verifying Data Integrity...")
        errors = 0

        # 1. Batch quantities match movements
        for batch in Batch.objects.all():
            movement_total = StockMovement.objects.filter(batch=batch).aggregate(Sum('qty'))['qty__sum'] or 0
            if batch.remaining_qty != movement_total:
                self.stderr.write(f"ERROR: Batch {batch.batch_code} remaining ({batch.remaining_qty}) != movements ({movement_total})")
                errors += 1

        # 2. Balances match sum of batches
        for bal in SKUBalance.objects.all():
            batch_total = Batch.objects.filter(sku=bal.sku).aggregate(Sum('remaining_qty'))['remaining_qty__sum'] or 0
            if bal.qty != batch_total:
                self.stderr.write(f"ERROR: SKU {bal.sku.code} balance ({bal.qty}) != batch total ({batch_total})")
                errors += 1

        # 3. Allocations match SaleLines
        for line in SaleLine.objects.all():
            alloc_total = SaleAllocation.objects.filter(sale_line=line).aggregate(Sum('qty'))['qty__sum'] or 0
            if line.qty != alloc_total:
                self.stderr.write(f"ERROR: SaleLine {line.id} qty ({line.qty}) != allocations ({alloc_total})")
                errors += 1

        if errors == 0:
            self.stdout.write(self.style.SUCCESS("All integrity checks passed perfectly."))
        else:
            self.stdout.write(self.style.ERROR(f"{errors} integrity errors found."))