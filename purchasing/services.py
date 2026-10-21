from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audit.services import record
from costing.services import update_average_cost
from inventory.models import Batch, Location, SKU, StockMovement

from .models import Receipt, ReceiptLine, Supplier


@transaction.atomic
def receive_stock(
    *,
    supplier: Supplier,
    sku: SKU,
    location: Location,
    qty: Decimal | int,
    unit_cost: Decimal | int,
    expiry_date: date,
    reference: str = "",
) -> Receipt:
    """
    Record an incoming purchase for one SKU. Writes — atomically:

      Receipt (header)
      Batch (physical lot, with expiry for FEFO)
      StockMovement (append-only RECEIVE entry)
      ReceiptLine (links the three)
      SKUBalance update (weighted average cost)
      AuditLog entry

    If any step fails, nothing is written.
    """
    qty = Decimal(qty)
    unit_cost = Decimal(unit_cost)

    if qty <= 0:
        raise ValidationError({"qty": "must be positive"})
    if unit_cost < 0:
        raise ValidationError({"unit_cost": "cannot be negative"})

    receipt = Receipt.objects.create(supplier=supplier, reference=reference)

    batch = Batch(
        sku=sku, location=location,
        received_at=timezone.now(),
        expiry_date=expiry_date,
        received_qty=qty, remaining_qty=qty,
        unit_cost=unit_cost,
        reference=reference,
    )
    batch.save()  # full_clean() runs inside Batch.save() now

    movement = StockMovement.objects.create(
        sku=sku, location=location, batch=batch,
        movement_type=StockMovement.MovementType.RECEIVE,
        qty=qty, unit_cost=unit_cost, reference=reference,
    )

    ReceiptLine.objects.create(
        receipt=receipt, sku=sku, location=location,
        qty=qty, unit_cost=unit_cost, expiry_date=expiry_date,
        batch=batch, stock_movement=movement,
    )

    update_average_cost(sku=sku, qty=qty, unit_cost=unit_cost)

    record(
        action="receive_stock",
        target=f"{sku.code} × {qty}",
        payload={
            "receipt_id": receipt.pk,
            "batch_id": batch.pk,
            "movement_id": movement.pk,
            "unit_cost": str(unit_cost),
        },
    )

    return receipt