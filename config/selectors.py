from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum, F, Count, Q
from django.utils import timezone

from costing.models import SKUBalance
from inventory.models import Batch, StockMovement
from sales.models import Sale, SaleLine


def get_dashboard_metrics(user):
    today = date.today()
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)

    # 1. Inventory Counts (visible to all staff)
    available_skus = SKUBalance.objects.filter(qty__gt=0).count()
    expired_batches = Batch.objects.filter(expiry_date__lt=today).count()

    # 2. Expiring soon (next 30 days)
    warning_threshold = today + timedelta(days=30)
    expiring_batches = Batch.objects.filter(
        expiry_date__gte=today,
        expiry_date__lte=warning_threshold
    ).count()

    # 3. Cost & Valuation (gated by permission)
    total_stock_value = Decimal("0.00")
    if user.has_perm("costing.view_costs"):
        # Sum of (qty * avg_cost) across all SKU balances
        agg = SKUBalance.objects.aggregate(
            total_value=Sum(F("qty") * F("avg_cost"))
        )
        total_stock_value = agg["total_value"] or Decimal("0.00")

    # 4. Sales Metrics (gated by permission)
    sales_count = 0
    sales_total = Decimal("0.00")
    gross_profit = Decimal("0.00")

    if user.has_perm("sales.view_sale"):
        sales_agg = Sale.objects.filter(occurred_at__gte=thirty_days_ago).aggregate(
            count=Count("id"),
            total=Sum("total_price")
        )
        sales_count = sales_agg["count"] or 0
        sales_total = sales_agg["total"] or Decimal("0.00")

    if user.has_perm("costing.view_costs"):
        # Gross Profit = (unit_price - unit_cost) * qty
        profit_agg = SaleLine.objects.filter(
            sale__occurred_at__gte=thirty_days_ago
        ).aggregate(
            profit=Sum((F("unit_price") - F("unit_cost")) * F("qty"))
        )
        gross_profit = profit_agg["profit"] or Decimal("0.00")

    if user.has_perm("sales.view_sale"):
        # NEW: Filter dashboard metrics if they lack view_all_sales
        sales_qs = Sale.objects.filter(occurred_at__gte=thirty_days_ago)
        if not user.has_perm("sales.view_all_sales"):
            sales_qs = sales_qs.filter(sold_by=user)

        sales_agg = sales_qs.aggregate(
            count=Count("id"),
            total=Sum("total_price")
        )
        sales_count = sales_agg["count"] or 0
        sales_total = sales_agg["total"] or Decimal("0.00")

    return {
        "available_skus": available_skus,
        "expired_batches": expired_batches,
        "expiring_batches": expiring_batches,
        "total_stock_value": total_stock_value,
        "sales_count": sales_count,
        "sales_total": sales_total,
        "gross_profit": gross_profit,
    }


def get_recent_activity(limit=10):
    return StockMovement.objects.select_related("sku", "location", "user").order_by("-occurred_at")[:limit]


def get_valuation_report():
    """Inventory valuation: Quantity * Avg Cost per SKU."""
    return SKUBalance.objects.select_related("sku", "sku__product").filter(
        qty__gt=0
    ).order_by("sku__code")

def get_sales_performance_report(days=30):
    """Sales grouped by customer for the last N days."""
    cutoff = timezone.now() - timedelta(days=days)
    return Sale.objects.filter(occurred_at__gte=cutoff).values(
        "customer__name"
    ).annotate(
        total_revenue=Sum("total_price"),
        transaction_count=Count("id")
    ).order_by("-total_revenue")

def get_expiry_report():
    """All batches with remaining stock, ordered by expiry."""
    return Batch.objects.select_related("sku", "location").filter(
        remaining_qty__gt=0
    ).order_by("expiry_date")

def get_audit_logs():
    """Recent audit history."""
    from audit.models import AuditLog
    return AuditLog.objects.order_by("-created_at")[:100]