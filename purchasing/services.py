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
    reference: str = "",
    user=None,             # <-- Standardized actor argument (Section 7.1)
    received_by=None,      # <-- Backward compatibility
    lines: list = None,    # <-- Multi-line support
    **kwargs
) -> Receipt:

    """
    Record an incoming purchase atomically.
    """
    actor = user or received_by

    if lines is None:
        # Backward compatibility wrapper for single-line calls
        lines = [{
            'sku': kwargs.get('sku'),
            'location': kwargs.get('location'),
            'qty': kwargs.get('qty'),
            'unit_cost': kwargs.get('unit_cost'),
            'expiry_date': kwargs.get('expiry_date'),
        }]

    if not lines:
        raise ValidationError("A receipt must have at least one line.")

    # Pre-validate all lines before committing
    for line in lines:
        if not line.get('sku') or not line.get('location'):
            raise ValidationError("SKU and Location are required on all lines.")
        if Decimal(line.get('qty', 0)) <= 0:
            raise ValidationError({"qty": "Quantity must be positive."})
        if Decimal(line.get('unit_cost', 0)) < 0:
            raise ValidationError({"unit_cost": "Cost cannot be negative."})
        if not line.get('expiry_date'):
            raise ValidationError("Expiry date is required.")

    receipt = Receipt.objects.create(
        supplier=supplier, reference=reference, received_by=actor,
    )

    for line_data in lines:
        sku = line_data['sku']
        location = line_data['location']
        qty = Decimal(line_data['qty'])
        unit_cost = Decimal(line_data['unit_cost'])
        expiry_date = line_data['expiry_date']

        batch = Batch(
            sku=sku, location=location,
            received_at=timezone.now(),
            expiry_date=expiry_date,
            received_qty=qty, remaining_qty=qty,
            unit_cost=unit_cost,
            reference=reference,
        )
        batch.save()

        movement = StockMovement.objects.create(
            sku=sku, location=location, batch=batch,
            movement_type=StockMovement.MovementType.RECEIVE,
            qty=qty, unit_cost=unit_cost, reference=reference,
            user=actor,  # Persisted to the existing 'user' field
        )

        ReceiptLine.objects.create(
            receipt=receipt, sku=sku, location=location,
            qty=qty, unit_cost=unit_cost, expiry_date=expiry_date,
            batch=batch, stock_movement=movement,
        )

        update_average_cost(sku=sku, qty=qty, unit_cost=unit_cost)

    record(
        action="receive_stock",
        target=f"Receipt #{receipt.pk}",
        payload={
            "receipt_id": receipt.pk,
            "line_count": len(lines),
        },
        user=actor,                        # <-- Added
        service="purchasing",              # <-- Added
        component="receipt_service"        # <-- Added
    )
    return receipt