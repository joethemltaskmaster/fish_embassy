from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from audit.services import record
from costing.models import SKUBalance
from costing.services import current_balance
from inventory.models import Batch, SKU, StockMovement

from .models import Customer, Sale, SaleAllocation, SaleLine


class InsufficientStock(Exception):
    """Requested qty exceeds available balance for the SKU."""


@transaction.atomic
def sell_stock(
    *,
    customer: Customer,
    sku: SKU,
    qty: Decimal | int,
    idempotency_key: str,
    unit_price: Decimal | int | None = None,
    reference: str = "",
) -> Sale:
    """
    Sell `qty` of `sku` to `customer`. Writes atomically:

      Sale, SaleLine (header + line, priced at selling_price or override)
      One SaleAllocation + one StockMovement per batch consumed (FEFO)
      SKUBalance decrement (avg_cost unchanged under average costing)
      AuditLog entry

    FEFO: batches are consumed in expiry_date order (earliest first).
    Row locking: SKUBalance row for this SKU is SELECT FOR UPDATE'd for the
    duration, so concurrent sales of the same SKU serialise — the last
    carton can only be sold once.

    Idempotency: same `idempotency_key` returns the existing Sale, writes
    nothing new. Protection against network-retry double-posting.
    """
    # Idempotency short-circuit — do this before any write.
    existing = Sale.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    qty = Decimal(qty)
    if qty <= 0:
        raise ValidationError({"qty": "must be positive"})

    # Serialise per SKU: any other transaction selling this SKU waits here.
    SKUBalance.objects.get_or_create(
        sku=sku, defaults={"qty": Decimal("0"), "avg_cost": Decimal("0")},
    )
    balance = SKUBalance.objects.select_for_update().get(sku=sku)

    if balance.qty < qty:
        raise InsufficientStock(
            f"Requested {qty} but only {balance.qty} on hand for {sku.code}."
        )

    effective_price = (
        Decimal(unit_price) if unit_price is not None else sku.selling_price
    )

    # Header — total_price set after the line is created
    sale = Sale.objects.create(
        customer=customer,
        idempotency_key=idempotency_key,
        reference=reference,
        total_price=Decimal("0"),
    )

    line = SaleLine.objects.create(
        sale=sale, sku=sku,
        qty=qty,
        unit_price=effective_price,
        unit_cost=balance.avg_cost,
    )

    # FEFO allocation: consume batches in expiry order, lock each as we go.
    remaining_to_consume = qty
    batches = (
        Batch.objects
        .select_for_update()
        .filter(sku=sku, remaining_qty__gt=0)
        .order_by("expiry_date", "received_at", "id")
    )

    for batch in batches:
        if remaining_to_consume <= 0:
            break

        take = min(batch.remaining_qty, remaining_to_consume)
        batch.remaining_qty -= take
        batch.save()   # full_clean() runs inside — remaining_qty >= 0 enforced

        movement = StockMovement.objects.create(
            sku=sku, location=batch.location, batch=batch,
            movement_type=StockMovement.MovementType.SALE,
            qty=-take,
            unit_cost=balance.avg_cost,
            reference=f"sale:{sale.pk}",
        )

        SaleAllocation.objects.create(
            sale_line=line, batch=batch, qty=take, stock_movement=movement,
        )

        remaining_to_consume -= take

    # Should not happen — the balance check above guarantees enough stock —
    # but if it does (data inconsistency), abort the whole sale loudly.
    if remaining_to_consume > 0:
        raise InsufficientStock(
            f"Batch inventory short by {remaining_to_consume} for {sku.code}. "
            f"Balance said {qty} available but batches couldn't cover it."
        )

    # Now finalize the sale's total and the SKU balance.
    sale.total_price = qty * effective_price
    sale.save()

    balance.qty -= qty
    balance.save()

    record(
        action="sell_stock",
        target=f"{sku.code} × {qty}",
        payload={
            "sale_id": sale.pk,
            "line_id": line.pk,
            "unit_price": str(effective_price),
            "unit_cost": str(balance.avg_cost),
            "total": str(sale.total_price),
            "allocations": [
                {"batch_id": a.batch_id, "qty": str(a.qty)}
                for a in line.allocations.all()
            ],
        },
    )

    return sale