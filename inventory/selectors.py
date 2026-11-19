"""
Inventory read queries. All ORM-level filtering and prefetching lives here
so views stay thin and templates stay query-free.
"""

from datetime import date, timedelta

from django.conf import settings
from django.db.models import Count, Q

from costing.models import SKUBalance

from .models import Batch, Location, Product, SKU, StockMovement


def products_for_list(*, search: str | None = None, is_active: bool | None = None):
    qs = Product.objects.annotate(sku_count=Count("skus")).order_by("name")
    if search:
        qs = qs.filter(name__icontains=search)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def skus_for_list(*, search: str | None = None, is_active: bool | None = None):
    qs = SKU.objects.select_related("product").order_by("code")
    if search:
        qs = qs.filter(
            Q(code__icontains=search) | Q(product__name__icontains=search)
        )
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def balances_for_list(*, search: str | None = None, has_stock_only: bool = True):
    qs = SKUBalance.objects.select_related("sku", "sku__product").order_by("sku__code")
    if search:
        qs = qs.filter(
            Q(sku__code__icontains=search) | Q(sku__product__name__icontains=search)
        )
    if has_stock_only:
        qs = qs.filter(qty__gt=0)
    return qs


def batches_for_list(*, search=None, expiry_status=None, location_code=None):
    qs = (
        Batch.objects
        .select_related("sku", "sku__product", "location", "receipt_line__receipt__supplier")
        .order_by("expiry_date", "received_at", "id")
    )
    if search:
        qs = qs.filter(Q(sku__code__icontains=search) | Q(reference__icontains=search))
    if location_code:
        qs = qs.filter(location__code=location_code)

    today = date.today()
    warning_days = getattr(settings, "RAO_EXPIRY_WARNING_DAYS", 30)
    threshold = today + timedelta(days=warning_days)

    if expiry_status == "expired":
        qs = qs.filter(expiry_date__lt=today)
    elif expiry_status == "expiring":
        qs = qs.filter(expiry_date__gte=today, expiry_date__lte=threshold)
    elif expiry_status == "fresh":
        qs = qs.filter(expiry_date__gt=threshold)
    return qs


def locations_for_list(*, search: str | None = None, is_active: bool | None = None):
    qs = Location.objects.annotate(batch_count=Count("batches")).order_by("code")
    if search:
        qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def movements_for_list(
    *,
    search: str | None = None,
    movement_type: str | None = None,
    since: date | None = None,
):
    qs = (
        StockMovement.objects
        .select_related("sku", "location", "batch")
        .order_by("-occurred_at", "-id")
    )
    if search:
        qs = qs.filter(Q(sku__code__icontains=search) | Q(reference__icontains=search))
    if movement_type:
        qs = qs.filter(movement_type=movement_type)
    if since:
        qs = qs.filter(occurred_at__date__gte=since)
    return qs


def expiry_status_for(batch: Batch, *, today: date | None = None) -> str:
    """Classify a batch: 'expired' | 'expiring' | 'fresh'."""
    today = today or date.today()
    warning_days = getattr(settings, "RAO_EXPIRY_WARNING_DAYS", 30)
    if batch.expiry_date < today:
        return "expired"
    if batch.expiry_date <= today + timedelta(days=warning_days):
        return "expiring"
    return "fresh"