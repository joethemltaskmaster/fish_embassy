
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import (
    Sum,
    F,
    ExpressionWrapper,
    DecimalField,
)
from django.utils import timezone
from costing.models import OperatingExpense
from costing.models import SKUBalance
from inventory.models import Batch
from sales.models import Sale, SaleLine


def _get_datetime_bounds(
    start_date: date,
    end_date: date,
):
    """
    Convert inclusive local date boundaries into timezone-aware
    datetime boundaries.
    """
    current_timezone = timezone.get_current_timezone()

    start_dt = timezone.make_aware(
        datetime.combine(start_date, time.min),
        current_timezone,
    )

    end_dt = timezone.make_aware(
        datetime.combine(end_date, time.max),
        current_timezone,
    )

    return start_dt, end_dt


def get_sales_summary(
    start_date: date,
    end_date: date,
) -> dict:
    """Calculate total revenue, units sold, and transaction count."""

    start_dt, end_dt = _get_datetime_bounds(
        start_date,
        end_date,
    )

    sales = Sale.objects.filter(
        occurred_at__range=(start_dt, end_dt)
    )

    revenue_agg = SaleLine.objects.filter(
        sale__in=sales
    ).aggregate(
        total_revenue=Sum(
            ExpressionWrapper(
                F("qty") * F("unit_price"),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            )
        ),
        total_qty=Sum("qty"),
    )

    revenue = (
        revenue_agg["total_revenue"]
        or Decimal("0.00")
    )

    qty = (
        revenue_agg["total_qty"]
        or Decimal("0.000")
    )

    return {
        "revenue": revenue,
        "units_sold": qty,
        "transaction_count": sales.count(),
    }


def get_gross_profit_summary(
    start_date: date,
    end_date: date,
) -> dict:
    """Calculate revenue, COGS, gross profit, and gross margin."""

    start_dt, end_dt = _get_datetime_bounds(
        start_date,
        end_date,
    )

    sales = Sale.objects.filter(
        occurred_at__range=(start_dt, end_dt)
    )

    lines = SaleLine.objects.filter(
        sale__in=sales
    )

    agg = lines.aggregate(
        revenue=Sum(
            ExpressionWrapper(
                F("qty") * F("unit_price"),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            )
        ),
        cogs=Sum(
            ExpressionWrapper(
                F("qty") * F("unit_cost"),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            )
        ),
    )

    revenue = agg["revenue"] or Decimal("0.00")
    cogs = agg["cogs"] or Decimal("0.00")

    gross_profit = revenue - cogs

    margin = Decimal("0.00")

    if revenue > 0:
        margin = (
            gross_profit / revenue
        ) * Decimal("100.00")

    return {
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "gross_margin_percent": round(margin, 2),
    }


def get_stock_valuation() -> dict:
    """Calculate current inventory value using average cost."""

    agg = SKUBalance.objects.aggregate(
        total_value=Sum(
            ExpressionWrapper(
                F("qty") * F("avg_cost"),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            )
        ),
        total_qty=Sum("qty"),
    )

    return {
        "total_inventory_value": (
            agg["total_value"] or Decimal("0.00")
        ),
        "total_units": (
            agg["total_qty"] or Decimal("0.000")
        ),
    }


def get_expiring_batches(
    days_ahead: int = 30,
) -> list:
    """Identify batches with stock expiring within the specified window."""

    today = timezone.localdate()

    threshold = today + timedelta(
        days=days_ahead
    )

    batches = (
        Batch.objects.filter(
            remaining_qty__gt=0,
            expiry_date__gte=today,
            expiry_date__lte=threshold,
        )
        .select_related("sku", "location")
        .order_by("expiry_date")
    )

    return [
        {
            "batch_code": batch.batch_code,
            "sku_code": batch.sku.code,
            "location": batch.location.code,
            "expiry_date": batch.expiry_date.isoformat(),
            "remaining_qty": batch.remaining_qty,
            "days_until_expiry": (
                batch.expiry_date - today
            ).days,
        }
        for batch in batches
    ]


def get_low_stock_products() -> list:
    """Identify SKUs whose current balance is at or below reorder level."""

    balances = (
        SKUBalance.objects.filter(
            qty__lte=F("sku__reorder_level")
        )
        .select_related(
            "sku",
            "sku__product",
        )
        .order_by("qty")
    )

    return [
        {
            "sku_code": balance.sku.code,
            "product_name": balance.sku.product.name,
            "current_qty": balance.qty,
            "reorder_level": balance.sku.reorder_level,
        }
        for balance in balances
    ]


def get_top_selling_products(
    start_date: date,
    end_date: date,
    limit: int = 5,
) -> list:
    """Rank SKUs by revenue generated during the specified period."""

    start_dt, end_dt = _get_datetime_bounds(
        start_date,
        end_date,
    )

    sales = Sale.objects.filter(
        occurred_at__range=(start_dt, end_dt)
    )

    top_skus = (
        SaleLine.objects.filter(
            sale__in=sales
        )
        .values(
            "sku__code",
            "sku__product__name",
        )
        .annotate(
            total_revenue=Sum(
                ExpressionWrapper(
                    F("qty") * F("unit_price"),
                    output_field=DecimalField(
                        max_digits=14,
                        decimal_places=2,
                    ),
                )
            ),
            total_qty=Sum("qty"),
        )
        .order_by("-total_revenue")[:limit]
    )

    return [
        {
            "sku_code": item["sku__code"],
            "product_name": item["sku__product__name"],
            "revenue": item["total_revenue"],
            "qty_sold": item["total_qty"],
        }
        for item in top_skus
    ]


def get_weekly_report_data(
    reference_date: date = None,
) -> dict:
    """
    Compose a Monday-Sunday weekly report.

    Defaults to the current date in Django's configured timezone.
    """

    if reference_date is None:
        reference_date = timezone.localdate()

    start_date = reference_date - timedelta(
        days=reference_date.weekday()
    )

    end_date = start_date + timedelta(days=6)

    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "sales": get_sales_summary(start_date, end_date),
        "profit": get_gross_profit_summary(start_date, end_date),
        "operating": get_operating_profit_summary(start_date, end_date),  # <-- NEW
        "top_products": get_top_selling_products(start_date, end_date),
        "inventory": get_stock_valuation(),
        "expiring": get_expiring_batches(),
        "low_stock": get_low_stock_products()
    }

def get_operating_profit_summary(start_date: date, end_date: date) -> dict:
    """Calculate gross profit, operating expenses, and operating profit."""
    gp = get_gross_profit_summary(start_date, end_date)

    expense_agg = OperatingExpense.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(total=Sum('amount'))

    expenses = expense_agg['total'] or Decimal('0.00')
    operating_profit = gp['gross_profit'] - expenses

    return {
        "gross_profit": gp['gross_profit'],
        "operating_expenses": expenses,
        "operating_profit": operating_profit
    }