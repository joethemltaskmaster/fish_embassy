
"""
Inventory browsing and registration views.

Browsing views are read-only in Phase 4a.

Security contract:
- Cost-bearing fields (selling_price, avg_cost, unit_cost, total value)
  are omitted entirely from response dictionaries when the user lacks
  `costing.view_costs`.
- Product, SKU and Location registration require their respective
  Django add permissions.
- The authenticated user is recorded in the created_by field.
"""

from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect

from costing.models import SKUBalance

from .form import ProductForm, SKUForm, LocationForm
from .models import Batch, Location, Product, SKU, StockMovement
from .selectors import (
    balances_for_list,
    batches_for_list,
    expiry_status_for,
    locations_for_list,
    movements_for_list,
    products_for_list,
    skus_for_list,
)


PAGE_SIZE = 25


def _can_view_costs(user) -> bool:
    return user.has_perm("costing.view_costs")


def _paginate(request, queryset, per_page=PAGE_SIZE):
    return Paginator(queryset, per_page).get_page(
        request.GET.get("page", 1)
    )


def _bool_param(value):
    if value in ("1", "true", "yes"):
        return True
    if value in ("0", "false", "no"):
        return False
    return None


def _query_wo_page(request):
    """Rebuild the current querystring minus 'page'."""
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


# ─────────────────────────────────────────────────────────────
# Hub
# ─────────────────────────────────────────────────────────────

@login_required
@permission_required("inventory.view_sku", raise_exception=True)
def index(request):
    today = date.today()
    warning_days = getattr(settings, "RAO_EXPIRY_WARNING_DAYS", 30)
    threshold = today + timedelta(days=warning_days)

    context = {
        "active_section": "inventory",
        "active_inventory": "overview",
        "counts": {
            "products": Product.objects.count(),
            "skus": SKU.objects.count(),
            "balances": SKUBalance.objects.filter(qty__gt=0).count(),
            "batches": Batch.objects.count(),
            "locations": Location.objects.count(),
            "movements": StockMovement.objects.count(),
        },
        "expiry": {
            "expired": Batch.objects.filter(
                expiry_date__lt=today
            ).count(),
            "expiring": Batch.objects.filter(
                expiry_date__gte=today,
                expiry_date__lte=threshold,
            ).count(),
        },
    }

    return render(request, "inventory/index.html", context)


# ─────────────────────────────────────────────────────────────
# Products — Read
# ─────────────────────────────────────────────────────────────

@login_required
@permission_required("inventory.view_product", raise_exception=True)
def products_list(request):
    search = request.GET.get("q", "").strip() or None
    is_active = _bool_param(request.GET.get("active"))

    qs = products_for_list(
        search=search,
        is_active=is_active,
    )

    page = _paginate(request, qs)

    rows = [
        {
            "pk": p.pk,
            "name": p.name,
            "sku_count": p.sku_count,
            "is_active": p.is_active,
        }
        for p in page.object_list
    ]

    return render(request, "inventory/products/list.html", {
        "active_section": "inventory",
        "active_inventory": "products",
        "rows": rows,
        "page": page,
        "search": search or "",
        "is_active": is_active,
        "querystring": _query_wo_page(request),
    })


# ─────────────────────────────────────────────────────────────
# Products — Create
# ─────────────────────────────────────────────────────────────

@login_required
@permission_required("inventory.add_product", raise_exception=True)
def product_create(request):
    """Register a new product."""

    if request.method == "POST":
        form = ProductForm(request.POST)

        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()

            messages.success(
                request,
                f"Product '{product.name}' registered successfully."
            )

            return redirect("inventory:products")

    else:
        form = ProductForm()

    return render(request, "inventory/products/create.html", {
        "form": form,
        "active_section": "inventory",
        "active_inventory": "products",
    })


# ─────────────────────────────────────────────────────────────
# SKUs — Read
# ─────────────────────────────────────────────────────────────

@login_required
@permission_required("inventory.view_sku", raise_exception=True)
def skus_list(request):
    search = request.GET.get("q", "").strip() or None
    is_active = _bool_param(request.GET.get("active"))
    show_costs = _can_view_costs(request.user)

    qs = skus_for_list(
        search=search,
        is_active=is_active,
    )

    page = _paginate(request, qs)

    rows = []

    for sku in page.object_list:
        row = {
            "pk": sku.pk,
            "code": sku.code,
            "product_name": sku.product.name,
            "unit_weight_kg": sku.unit_weight_kg,
            "base_unit": sku.base_unit,
            "is_active": sku.is_active,
        }

        if show_costs:
            row["selling_price"] = sku.selling_price

        rows.append(row)

    return render(request, "inventory/skus/list.html", {
        "active_section": "inventory",
        "active_inventory": "skus",
        "rows": rows,
        "page": page,
        "show_costs": show_costs,
        "search": search or "",
        "is_active": is_active,
        "querystring": _query_wo_page(request),
    })


# ─────────────────────────────────────────────────────────────
# SKUs — Create
# ─────────────────────────────────────────────────────────────

@login_required
@permission_required("inventory.add_sku", raise_exception=True)
def sku_create(request):
    """Register a new SKU."""

    if request.method == "POST":
        form = SKUForm(request.POST)

        if form.is_valid():
            sku = form.save(commit=False)
            sku.created_by = request.user
            sku.save()

            messages.success(
                request,
                f"SKU '{sku.code}' registered successfully."
            )

            return redirect("inventory:skus")

    else:
        form = SKUForm()

    return render(request, "inventory/skus/create.html", {
        "form": form,
        "active_section": "inventory",
        "active_inventory": "skus",
    })


# ─────────────────────────────────────────────────────────────
# Balances — Read
# ─────────────────────────────────────────────────────────────

@login_required
@permission_required("costing.view_skubalance", raise_exception=True)
def balances_list(request):
    search = request.GET.get("q", "").strip() or None
    has_stock_only = request.GET.get("has_stock") != "0"
    show_costs = _can_view_costs(request.user)

    qs = balances_for_list(
        search=search,
        has_stock_only=has_stock_only,
    )

    page = _paginate(request, qs)

    rows = []

    for bal in page.object_list:
        row = {
            "sku_code": bal.sku.code,
            "product_name": bal.sku.product.name,
            "qty": bal.qty,
        }

        if show_costs:
            row["avg_cost"] = bal.avg_cost
            row["value"] = bal.qty * bal.avg_cost

        rows.append(row)

    return render(request, "inventory/balances/list.html", {
        "active_section": "inventory",
        "active_inventory": "balances",
        "rows": rows,
        "page": page,
        "show_costs": show_costs,
        "search": search or "",
        "has_stock_only": has_stock_only,
        "querystring": _query_wo_page(request),
    })


# ─────────────────────────────────────────────────────────────
# Batches — Read
# ─────────────────────────────────────────────────────────────

@login_required
@permission_required("inventory.view_batch", raise_exception=True)
def batches_list(request):
    search = request.GET.get("q", "").strip() or None
    expiry_status = request.GET.get("expiry") or None
    location_code = request.GET.get("loc") or None
    show_costs = _can_view_costs(request.user)

    if expiry_status not in (None, "expired", "expiring", "fresh"):
        expiry_status = None

    qs = batches_for_list(
        search=search,
        expiry_status=expiry_status,
        location_code=location_code,
    )

    page = _paginate(request, qs)

    today = date.today()
    rows = []

    for batch in page.object_list:
        row = {
            "pk": batch.pk,
            "batch_code": batch.batch_code,
            "sku_code": batch.sku.code,
            "product_name": batch.sku.product.name,
            "location_code": batch.location.code,
            "expiry_date": batch.expiry_date,
            "received_qty": batch.received_qty,
            "remaining_qty": batch.remaining_qty,
            "status": expiry_status_for(batch, today=today),
            "supplier_name": batch.receipt_line.receipt.supplier.name if hasattr(batch,
                                                                                 'receipt_line') else "Adjustment",
        }

        if show_costs:
            row["unit_cost"] = batch.unit_cost
            row["value"] = batch.remaining_qty * batch.unit_cost

        rows.append(row)

    locations = Location.objects.filter(
        is_active=True
    ).order_by("code")

    return render(request, "inventory/batches/list.html", {
        "active_section": "inventory",
        "active_inventory": "batches",
        "rows": rows,
        "page": page,
        "show_costs": show_costs,
        "search": search or "",
        "expiry_status": expiry_status,
        "location_code": location_code,
        "locations": locations,
        "querystring": _query_wo_page(request),
    })


# ─────────────────────────────────────────────────────────────
# Locations — Read
# ─────────────────────────────────────────────────────────────

@login_required
@permission_required("inventory.view_location", raise_exception=True)
def locations_list(request):
    search = request.GET.get("q", "").strip() or None
    is_active = _bool_param(request.GET.get("active"))

    qs = locations_for_list(
        search=search,
        is_active=is_active,
    )

    page = _paginate(request, qs)

    rows = [
        {
            "pk": loc.pk,
            "code": loc.code,
            "name": loc.name,
            "batch_count": loc.batch_count,
            "is_active": loc.is_active,
        }
        for loc in page.object_list
    ]

    return render(request, "inventory/locations/list.html", {
        "active_section": "inventory",
        "active_inventory": "locations",
        "rows": rows,
        "page": page,
        "search": search or "",
        "is_active": is_active,
        "querystring": _query_wo_page(request),
    })


# ─────────────────────────────────────────────────────────────
# Locations — Create
# ─────────────────────────────────────────────────────────────

@login_required
@permission_required("inventory.add_location", raise_exception=True)
def location_create(request):
    """Register a new physical storage location."""

    if request.method == "POST":
        form = LocationForm(request.POST)

        if form.is_valid():
            location = form.save(commit=False)
            location.created_by = request.user
            location.save()

            messages.success(
                request,
                f"Storage location '{location.name}' registered successfully."
            )

            return redirect("inventory:locations")

    else:
        form = LocationForm()

    return render(request, "inventory/locations/create.html", {
        "form": form,
        "active_section": "inventory",
        "active_inventory": "locations",
    })


# ─────────────────────────────────────────────────────────────
# Movements — Read-only, append-only
# ─────────────────────────────────────────────────────────────

@login_required
@permission_required("inventory.view_stockmovement", raise_exception=True)
def movements_list(request):
    search = request.GET.get("q", "").strip() or None
    movement_type = request.GET.get("type") or None
    show_costs = _can_view_costs(request.user)

    if movement_type not in (None, "RECEIVE", "SALE", "ADJUST"):
        movement_type = None

    qs = movements_for_list(
        search=search,
        movement_type=movement_type,
    )

    page = _paginate(request, qs)

    rows = []

    for mv in page.object_list:
        row = {
            "pk": mv.pk,
            "occurred_at": mv.occurred_at,
            "movement_type": mv.movement_type,
            "sku_code": mv.sku.code,
            "location_code": mv.location.code,
            "qty": mv.qty,
            "reference": mv.reference,
        }

        if show_costs:
            row["unit_cost"] = mv.unit_cost

        rows.append(row)

    return render(request, "inventory/movements/list.html", {
        "active_section": "inventory",
        "active_inventory": "movements",
        "rows": rows,
        "page": page,
        "show_costs": show_costs,
        "search": search or "",
        "movement_type": movement_type,
        "querystring": _query_wo_page(request),
    })
