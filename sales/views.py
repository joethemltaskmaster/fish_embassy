import uuid
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect

from inventory.models import Batch
from .forms import CustomerForm
from .forms import SellStockForm
from .models import Sale
from .selectors import customers_for_list, sales_for_list
from .services import sell_stock, InsufficientStock

PAGE_SIZE = 25


def _paginate(request, qs):
    return Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page", 1))


def _query_wo_page(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


@login_required
@permission_required("sales.add_sale", raise_exception=True)
def index(request):
    return render(request, "sales/index.html", {
        "active_section": "sales",
        "counts": {
            "customers": customers_for_list().count(),
            "sales": sales_for_list().count(),
        }
    })


@login_required
@permission_required("sales.add_sale", raise_exception=True)
def customers_list(request):
    search = request.GET.get("q", "").strip() or None
    qs = customers_for_list(search=search)
    page = _paginate(request, qs)
    return render(request, "sales/customers/list.html", {
        "active_section": "sales",
        "rows": page.object_list,
        "page": page,
        "search": search or "",
        "querystring": _query_wo_page(request),
    })


@login_required
@permission_required("sales.view_sale", raise_exception=True)
def sales_list(request):
    search = request.GET.get("q", "").strip() or None

    # All authorized sales users see the shared sales history.
    # Individual ownership remains recorded in Sale.sold_by.
    qs = sales_for_list(search=search)

    page = _paginate(request, qs)

    return render(request, "sales/list.html", {
        "active_section": "sales",
        "rows": page.object_list,
        "page": page,
        "search": search or "",
        "querystring": _query_wo_page(request),
    })


@login_required
@permission_required("sales.add_customer", raise_exception=True)
def customer_create(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user  # <-- Added audit trail
            obj.save()
            messages.success(request, "Customer registered successfully.")
            return redirect("sales:customers")
    else:
        form = CustomerForm()
    return render(request, "sales/customers/create.html", {"active_section": "sales", "form": form})

@login_required
@permission_required("sales.add_sale", raise_exception=True)
def sell(request):
    if request.method == "POST":
        form = SellStockForm(request.POST)
        if form.is_valid():
            try:
                sale = sell_stock(
                    customer=form.cleaned_data['customer'],
                    sku=form.cleaned_data['sku'],
                    qty=form.cleaned_data['qty'],
                    idempotency_key=form.cleaned_data['idempotency_key'],
                    reference=form.cleaned_data['reference'],
                    sold_by=request.user,
                    occurred_at=form.cleaned_data['occurred_at']  # <-- Ensure this is here
                )
                messages.success(
                    request,
                    f"Successfully recorded sale #{sale.pk}. Total: ₦{sale.total_price:,.2f}"
                )
                return redirect("sales:list")
            except InsufficientStock as e:
                messages.error(request, str(e))
            except ValidationError as e:
                # Handle selling_price validation error
                msg = e.messages[0] if hasattr(e, 'messages') else str(e)
                messages.error(request, f"Validation error: {msg}")
            except Exception as e:
                messages.error(request, f"Failed to record sale: {str(e)}")
    else:
        form = SellStockForm(initial={"idempotency_key": str(uuid.uuid4())})

    return render(request, "sales/sell.html", {
        "active_section": "sales",
        "form": form,
    })


@login_required
@permission_required("sales.add_sale", raise_exception=True)
def fefo_preview_api(request):
    """
    Read-only FEFO simulation. Returns the batches that *would* be consumed
    for the given SKU and quantity, without locking or modifying anything.
    """
    sku_id = request.GET.get("sku")
    qty_str = request.GET.get("qty")

    if not sku_id or not qty_str:
        return JsonResponse({"error": "sku and qty parameters are required."}, status=400)

    try:
        qty = Decimal(qty_str)
        if qty <= 0:
            return JsonResponse({"allocations": [], "sufficient": True})

        batches = (
            Batch.objects
            .filter(sku_id=sku_id, remaining_qty__gt=0)
            .select_related("location")
            .order_by("expiry_date", "received_at", "id")
        )

        allocations = []
        remaining_to_consume = qty

        for batch in batches:
            if remaining_to_consume <= 0:
                break
            take = min(batch.remaining_qty, remaining_to_consume)
            allocations.append({
                "batch_id": batch.pk,
                "expiry_date": batch.expiry_date.strftime("%d %b %Y"),
                "location": batch.location.code,
                "qty": str(take),
            })
            remaining_to_consume -= take

        return JsonResponse({
            "allocations": allocations,
            "sufficient": remaining_to_consume <= 0,
            "shortfall": str(remaining_to_consume) if remaining_to_consume > 0 else "0"
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)