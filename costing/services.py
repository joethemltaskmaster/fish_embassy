from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from inventory.models import SKU

from .models import SKUBalance


_TWO_PLACES = Decimal("0.01")


def current_balance(sku: SKU) -> SKUBalance:
    """
    Return the SKU's balance row.

    If no balance exists yet, create a zeroed balance.
    """

    balance, _ = SKUBalance.objects.get_or_create(
        sku=sku,
        defaults={
            "qty": Decimal("0.000"),
            "avg_cost": Decimal("0.00"),
        },
    )

    return balance


@transaction.atomic
def update_average_cost(
    *,
    sku: SKU,
    qty: Decimal,
    unit_cost: Decimal,
) -> SKUBalance:
    """
    Update the weighted-average cost after stock is received.

    Formula:

        new average cost =
            (
                old quantity * old average cost
                +
                incoming quantity * incoming unit cost
            )
            /
            total quantity

    The balance row is locked so concurrent receiving operations
    cannot overwrite one another's calculations.
    """

    qty = Decimal(str(qty))
    unit_cost = Decimal(str(unit_cost))

    if qty <= 0:
        raise ValueError(
            "Incoming quantity must be greater than zero."
        )

    if unit_cost < 0:
        raise ValueError(
            "Unit cost cannot be negative."
        )

    # Ensure the balance row exists.
    SKUBalance.objects.get_or_create(
        sku=sku,
        defaults={
            "qty": Decimal("0.000"),
            "avg_cost": Decimal("0.00"),
        },
    )

    # Lock the balance row before calculating the new average.
    balance = (
        SKUBalance.objects.select_for_update()
        .get(sku=sku)
    )

    old_qty = balance.qty
    old_avg = balance.avg_cost

    new_qty = old_qty + qty

    if new_qty <= 0:
        raise ValueError(
            f"Total quantity would be non-positive ({new_qty})."
        )

    total_value = (
        old_qty * old_avg
        +
        qty * unit_cost
    )

    new_avg = (
        total_value / new_qty
    ).quantize(
        _TWO_PLACES,
        rounding=ROUND_HALF_UP,
    )

    balance.qty = new_qty
    balance.avg_cost = new_avg

    balance.save()

    return balance
