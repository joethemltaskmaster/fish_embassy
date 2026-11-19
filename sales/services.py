
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from audit.services import record
from costing.models import SKUBalance
from inventory.models import SKU, Batch, StockMovement

from .models import Customer, Sale, SaleAllocation, SaleLine


class InsufficientStock(Exception):
    """Raised when a sale requests more stock than is available."""
    pass


def _to_decimal(value, field_name):
    """Convert an input to Decimal and reject invalid numeric values."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({
            field_name: "Enter a valid numeric value."
        })

    if not amount.is_finite():
        raise ValidationError({
            field_name: "Enter a finite numeric value."
        })

    return amount


@transaction.atomic
def sell_stock(
    *,
    customer: Customer,
    idempotency_key,
    reference="",
    user=None,
    sold_by=None,
    lines=None,
    occurred_at=None,
    **kwargs,
):
    """
    Record a sale and consume stock using FEFO allocation.

    Responsibilities:
    1. Prevent duplicate sales using the idempotency key.
    2. Validate and consolidate requested SKU quantities.
    3. Lock SKU balances and prevent overselling.
    4. Create the Sale and SaleLine records.
    5. Consume eligible batches using FEFO.
    6. Record stock movements and sale allocations.
    7. Update SKU balances.
    8. Record the audit event.

    The entire operation is atomic. If any step fails, all database
    changes made during this sale are rolled back.
    """

    actor = user if user is not None else sold_by

    if occurred_at is None:
        occurred_at = timezone.now()

    if not idempotency_key or not str(idempotency_key).strip():
        raise ValidationError({
            "idempotency_key": "An idempotency key is required."
        })

    # ---------------------------------------------------------
    # 1. Database-backed idempotency check
    # ---------------------------------------------------------
    # Check BEFORE creating a new Sale.
    existing = Sale.objects.filter(
        idempotency_key=idempotency_key
    ).first()

    if existing:
        return existing

    # ---------------------------------------------------------
    # 2. Support both multi-line and legacy single-line sales
    # ---------------------------------------------------------
    if lines is None:
        lines = [
            {
                "sku": kwargs.get("sku"),
                "qty": kwargs.get("qty"),
                "unit_price": kwargs.get("unit_price"),
            }
        ]

    if not lines:
        raise ValidationError(
            "A sale must contain at least one line."
        )

    # ---------------------------------------------------------
    # 3. Validate and consolidate SKU demand
    # ---------------------------------------------------------
    # Multiple entries for the same SKU are combined.
    # Conflicting prices for the same SKU are rejected.
    demand_map = {}

    for line in lines:
        if not isinstance(line, dict):
            raise ValidationError(
                "Each sale line must be a dictionary."
            )

        sku = line.get("sku")

        if not isinstance(sku, SKU) or sku.pk is None:
            raise ValidationError({
                "sku": "A valid saved SKU is required."
            })

        qty = _to_decimal(
            line.get("qty", 0),
            "qty",
        )

        if qty <= 0:
            raise ValidationError({
                "qty": "Quantity must be positive."
            })

        raw_price = line.get("unit_price")

        if raw_price is None or raw_price == "":
            raw_price = sku.selling_price

        price = _to_decimal(
            raw_price,
            "unit_price",
        )

        if price <= 0:
            raise ValidationError({
                "sku": (
                    f"SKU {sku.code} does not have "
                    "a valid selling price."
                )
            })

        if sku.pk in demand_map:
            existing_price = demand_map[sku.pk]["unit_price"]

            if existing_price != price:
                raise ValidationError({
                    "lines": (
                        f"Conflicting prices submitted "
                        f"for SKU {sku.code}."
                    )
                })

            demand_map[sku.pk]["qty"] += qty

        else:
            demand_map[sku.pk] = {
                "sku": sku,
                "qty": qty,
                "unit_price": price,
            }

    # ---------------------------------------------------------
    # 4. Create the Sale header
    # ---------------------------------------------------------
    # The nested atomic block creates a savepoint. This allows us
    # to catch a duplicate-key IntegrityError without breaking
    # the surrounding transaction.
    try:
        with transaction.atomic():
            sale = Sale.objects.create(
                customer=customer,
                idempotency_key=idempotency_key,
                reference=reference,
                total_price=Decimal("0.00"),
                sold_by=actor,
                occurred_at=occurred_at,
            )

    except IntegrityError:
        # Another request may have created this idempotency key
        # after our initial check.
        existing = Sale.objects.filter(
            idempotency_key=idempotency_key
        ).first()

        if existing:
            return existing

        # Do not hide unrelated database integrity errors.
        raise

    # ---------------------------------------------------------
    # 5. Lock SKU balances in deterministic order
    # ---------------------------------------------------------
    # Sorting SKU IDs helps prevent deadlocks when two sales
    # attempt to consume multiple SKUs simultaneously.
    sorted_sku_ids = sorted(demand_map.keys())

    locked_balances = {}

    for sku_id in sorted_sku_ids:
        sku = demand_map[sku_id]["sku"]

        SKUBalance.objects.get_or_create(
            sku=sku,
            defaults={
                "qty": Decimal("0.000"),
                "avg_cost": Decimal("0.00"),
            },
        )

        balance = SKUBalance.objects.select_for_update().get(
            sku=sku
        )

        requested_qty = demand_map[sku_id]["qty"]

        if balance.qty < requested_qty:
            raise InsufficientStock(
                f"Requested {requested_qty}, but only "
                f"{balance.qty} on hand for {sku.code}."
            )

        locked_balances[sku_id] = balance

    # ---------------------------------------------------------
    # 6. Process each SKU and allocate stock using FEFO
    # ---------------------------------------------------------
    total_sale_price = Decimal("0.00")
    today = timezone.localdate()

    for sku_id in sorted_sku_ids:
        data = demand_map[sku_id]

        sku = data["sku"]
        qty = data["qty"]
        price = data["unit_price"]

        balance = locked_balances[sku_id]

        # Capture the average cost at the time of sale.
        sale_line = SaleLine.objects.create(
            sale=sale,
            sku=sku,
            qty=qty,
            unit_price=price,
            unit_cost=balance.avg_cost,
        )

        total_sale_price += qty * price

        remaining_to_consume = qty

        # FEFO: consume the earliest-expiring eligible batches first.
        batches = (
            Batch.objects.select_for_update()
            .filter(
                sku=sku,
                remaining_qty__gt=0,
                expiry_date__gte=today,
            )
            .order_by(
                "expiry_date",
                "received_at",
                "id",
            )
        )

        for batch in batches:
            if remaining_to_consume <= 0:
                break

            take = min(
                batch.remaining_qty,
                remaining_to_consume,
            )

            batch.remaining_qty -= take

            batch.save(
                update_fields=["remaining_qty"]
            )

            # Record the stock leaving the business.
            movement = StockMovement.objects.create(
                sku=sku,
                location=batch.location,
                batch=batch,
                movement_type=StockMovement.MovementType.SALE,
                qty=-take,
                unit_cost=balance.avg_cost,
                reference=f"sale:{sale.pk}",
                user=actor,
            )

            # Connect the sale line to the batch consumed.
            SaleAllocation.objects.create(
                sale_line=sale_line,
                batch=batch,
                qty=take,
                stock_movement=movement,
            )

            remaining_to_consume -= take

        # The batch records must support the quantity being sold.
        if remaining_to_consume > 0:
            raise InsufficientStock(
                f"Batch inventory is short by "
                f"{remaining_to_consume} for {sku.code}."
            )

        # Update the authoritative SKU balance.
        balance.qty -= qty

        balance.save(
            update_fields=["qty", "updated_at"]
        )

    # ---------------------------------------------------------
    # 7. Finalise the Sale header
    # ---------------------------------------------------------
    sale.total_price = total_sale_price

    sale.save(
        update_fields=["total_price"]
    )

    # ---------------------------------------------------------
    # 8. Record the audit event
    # ---------------------------------------------------------
    record(
        action="sell_stock",
        target=f"Sale #{sale.pk}",
        payload={
            "sale_id": sale.pk,
            "total": str(sale.total_price),
            "user_id": actor.pk if actor else None,
        },
    )

    return sale
