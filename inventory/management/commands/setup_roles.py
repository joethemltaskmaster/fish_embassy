"""
Idempotent role setup. Creates or updates the Manager and Inventory Staff
groups and assigns the exact permission set defined here.

Safe to run repeatedly — each run reconciles group permissions to the
current definition, adding new ones and removing stale ones. Does NOT
touch superusers, does NOT create demo users, does NOT modify business data.

Run after every deployment that changes permissions:
    python manage.py setup_roles
"""

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


# ─────────────────────────────────────────────────────────────
# Role → permission codenames. All names are "<app_label>.<codename>".
# ─────────────────────────────────────────────────────────────
ROLE_PERMISSIONS = {
    "Manager": [
        # Inventory — full read, can approve adjustments
        "inventory.view_product",
        "inventory.view_sku",
        "inventory.view_batch",
        "inventory.view_stockmovement",
        "inventory.view_location",
        "inventory.approve_adjustments",

        # Purchasing — full read + record receipts
        "purchasing.view_supplier",
        "purchasing.view_receipt",
        "purchasing.view_receiptline",
        "purchasing.add_receipt",

        # Sales — full read + record sales
        "sales.view_customer",
        "sales.view_sale",
        "sales.view_saleline",
        "sales.view_saleallocation",
        "sales.add_sale",

        # Costing — can see costs and reports
        "costing.view_skubalance",
        "costing.view_costs",
        "costing.view_reports",

        # Audit — full read
        "audit.view_auditlog",
        "audit.view_audit_history",
    ],

    "Inventory Staff": [
        # Inventory — full read
        "inventory.view_product",
        "inventory.view_sku",
        "inventory.view_batch",
        "inventory.view_stockmovement",
        "inventory.view_location",

        # Purchasing — full read + record receipts
        "purchasing.view_supplier",
        "purchasing.view_receipt",
        "purchasing.view_receiptline",
        "purchasing.add_receipt",

        # Explicitly NOT: any sales.*, any costing.view_costs/view_reports,
        # any audit.*, inventory.approve_adjustments
    ],
}


class Command(BaseCommand):
    help = "Create or update Manager and Inventory Staff groups with defined permissions."

    def handle(self, *args, **options):
        for role_name, codenames in ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=role_name)
            verb = "created" if created else "updated"

            perms = []
            missing = []
            for cn in codenames:
                try:
                    app_label, codename = cn.split(".", 1)
                    perm = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                    perms.append(perm)
                except Permission.DoesNotExist:
                    missing.append(cn)
                except ValueError:
                    missing.append(cn)

            group.permissions.set(perms)

            self.stdout.write(self.style.SUCCESS(
                f"{verb} group '{role_name}' with {len(perms)} permission(s)"
            ))
            if missing:
                self.stdout.write(self.style.WARNING(
                    f"  {len(missing)} permission(s) not found (run makemigrations/migrate first):"
                ))
                for m in missing:
                    self.stdout.write(f"    - {m}")

        self.stdout.write(self.style.SUCCESS(
            "Role setup complete. Assign users via /admin/auth/user/ "
            "or 'manage.py createsuperuser' for the superuser."
        ))