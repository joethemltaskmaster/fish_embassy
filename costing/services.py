from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from inventory.models import SKU

from .models import SKUBalance


_TWO_PLACES = Decimal("0.01")


def current_balance(sku: SKU) -> SKUBalance:
    """Return the SKU's balance row, creating a zeroed one if missing."""
    balance, _ = SKUBalance.objects.get_or_create(
        sku=sku, defaults={"qty": Decimal("0"), "avg_cost": Decimal("0")},
    )
    return balance


@transaction.atomic
def update_average_cost(
    *, sku: SKU, qty: Decimal, unit_cost: Decimal,
) -> SKUBalance:
    """
    Weighted-average update on an incoming purchase:
        new_avg = (old_qty * old_avg + qty * unit_cost) / (old_qty + qty)

    Row is locked for the duration, so concurrent receives serialise.
    """
    # Ensure the row exists outside the lock; then lock it.
    SKUBalance.objects.get_or_create(
        sku=sku, defaults={"qty": Decimal("0"), "avg_cost": Decimal("0")},
    )
    balance = SKUBalance.objects.select_for_update().get(sku=sku)

    old_qty = balance.qty
    old_avg = balance.avg_cost
    new_qty = old_qty + qty

    if new_qty <= 0:
        raise ValueError(f"Total qty would be non-positive ({new_qty}).")

    total_value = old_qty * old_avg + qty * unit_cost
    new_avg = (total_value / new_qty).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)

    balance.qty = new_qty
    balance.avg_cost = new_avg
    balance.save()
    return balance