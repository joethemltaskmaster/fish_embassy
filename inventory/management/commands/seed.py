import random
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from costing.models import SKUBalance
from inventory.models import Location, Product, SKU, Batch
from purchasing.models import Supplier, Receipt
from purchasing.services import receive_stock
from sales.models import Customer, Sale
from sales.services import sell_stock, InsufficientStock
from django.utils import timezone


class Command(BaseCommand):
    help = "Generate deterministic synthetic dataset for RAO Fish Embassy."

    def add_arguments(self, parser):
        parser.add_argument("--skip-stock", action="store_true", help="Only create master data.")
        parser.add_argument("--with-demo-users", action="store_true", help="Create demo users.")

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(42)  # Deterministic generation
        self.stdout.write("Seeding Master Data...")

        # 1. Locations
        locs = [Location.objects.get_or_create(code=f"LOC-{i}", defaults={"name": f"Freezer {i}"})[0] for i in
                range(1, 4)]

        # 2. Suppliers & Customers
        suppliers = [Supplier.objects.get_or_create(name=f"Supplier {i}")[0] for i in range(1, 7)]
        customers = [Customer.objects.get_or_create(name=f"Customer {i}")[0] for i in range(1, 21)]

        # 3. Products & SKUs (Strictly following Section 2.1)
        catalogue = [
            ("Frozen Chicken", "CHICKEN-20KG", Decimal("25000"), 20),
            ("Frozen Turkey", "TURKEY-10KG", Decimal("18000"), 10),
            ("Frozen Croaker", "CROAKER-10KG", Decimal("15000"), 10),
            ("Frozen Catfish", "CATFISH-10KG", Decimal("12000"), 10),
            ("Frozen Mackerel", "MACKEREL-10KG", Decimal("10000"), 10),
            ("Frozen Beef", "BEEF-5KG", Decimal("20000"), 5),
            ("Frozen Prawns", "PRAWNS-1KG", Decimal("8000"), 1),
        ]

        skus = []
        for prod_name, sku_code, price, weight in catalogue:
            prod, _ = Product.objects.get_or_create(name=prod_name)
            sku, _ = SKU.objects.get_or_create(
                code=sku_code,
                defaults={"product": prod, "selling_price": price, "unit_weight_kg": weight}
            )
            skus.append(sku)

        if opts["with_demo_users"]:
            self._create_demo_users()

        if opts["skip_stock"]:
            self.stdout.write(self.style.WARNING("Skipping stock generation."))
            return

        self.stdout.write("Seeding Transactions...")

        # 4. Generate Receipts (Multi-line allowed)
        for i in range(1, 21):
            ref = f"RCV-SEED-{i:03d}"
            # Correct Idempotency Check (Section 8)
            if Receipt.objects.filter(reference=ref).exists():
                continue

            lines = []
            # 1 to 3 lines per receipt
            for _ in range(random.randint(1, 3)):
                sku = random.choice(skus)
                # Cost is 80% of selling price
                cost = sku.selling_price * Decimal("0.8")
                lines.append({
                    'sku': sku,
                    'location': random.choice(locs),
                    'qty': Decimal(random.randint(20, 100)),
                    'unit_cost': cost,
                    'expiry_date': date.today() + timedelta(days=random.randint(30, 365))
                })

            now = timezone.now()

            # ... Inside the Receipt generation loop (i=1 to 20):
            days_ago = random.randint(30, 90)  # Receipts happened 1 to 3 months ago
            receipt_date = now - timedelta(days=days_ago)

            receive_stock(
                supplier=random.choice(suppliers),
                reference=ref,
                lines=lines,
                received_at=receipt_date  # Need to add 'received_at' to receive_stock signature
            )

            # ... Inside the Sale generation loop (i=1 to 40):
            days_ago = random.randint(1, 29)  # Sales happened in the last month
            sale_date = now - timedelta(days=days_ago)

            sell_stock(
                customer=random.choice(customers),
                idempotency_key=f"idem-{ref}",
                reference=ref,
                lines=lines,
                occurred_at=sale_date
            )



        # 5. Generate Sales (Multi-line allowed)
        for i in range(1, 41):
            ref = f"SAL-SEED-{i:03d}"
            if Sale.objects.filter(reference=ref).exists():
                continue

            lines = []
            for _ in range(random.randint(1, 2)):
                sku = random.choice(skus)
                # Ensure enough stock before building the line
                bal = SKUBalance.objects.get(sku=sku).qty
                if bal > 10:
                    lines.append({
                        'sku': sku,
                        'qty': Decimal(random.randint(1, 5)),
                    })

            if lines:
                try:
                    sell_stock(
                        customer=random.choice(customers),
                        idempotency_key=f"idem-{ref}",
                        reference=ref,
                        lines=lines
                    )
                except InsufficientStock as e:
                    self.stderr.write(f"Seed Sale skipped: {e}")
                except Exception as e:
                    # Do NOT silently swallow (Section 3, Rule 9)
                    self.stderr.write(self.style.ERROR(f"Seed Sale failed: {str(e)}"))
                    raise

        self.stdout.write(self.style.SUCCESS("Seeding complete."))

    def _create_demo_users(self):
        User = get_user_model()
        password = "demo-pass-change-me"

        users = [
            ("manager_demo", "Manager"),
            ("staff_demo", "Inventory Staff"),
            ("sales_demo", "Sales Staff"),
            ("super_user", None),
        ]

        for username, group_name in users:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)

            if username == "super_user":
                user.is_superuser = True
                user.is_staff = True
            elif group_name:
                group = Group.objects.get(name=group_name)
                # Section 8: Force group assignment even if user exists
                user.groups.set([group])

            user.save()
            self.stdout.write(f"User {username} ready.")