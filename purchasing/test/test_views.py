import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from ..forms import ReceiveStockForm, ReceiveLineForm, SupplierForm
from ..models import Supplier
from ..selectors import receipts_for_list, suppliers_for_list
from ..services import receive_stock

PAGE_SIZE = 25


def _paginate(request, qs):
    return Paginator(qs, PAGE_SIZE).get_page(request.GET.get("page", 1))


def _query_wo_page(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


@login_required
@permission_required("purchasing.view_supplier", raise_exception=True)
def index(request):
    return render(request, "purchasing/index.html", {
        "active_section": "purchasing",
        "active_purchasing": "overview",
        "counts": {
            "suppliers": Supplier.objects.count(),
            "receipts": receipts_for_list().count(),
        }
    })


@login_required
@permission_required("purchasing.view_supplier", raise_exception=True)
def suppliers_list(request):
    search = request.GET.get("q", "").strip() or None
    qs = suppliers_for_list(search=search)
    page = _paginate(request, qs)
    return render(request, "purchasing/suppliers/list.html", {
        "active_section": "purchasing",
        "rows": page.object_list,
        "page": page,
        "search": search or "",
        "querystring": _query_wo_page(request),
    })


@login_required
@permission_required("purchasing.add_supplier", raise_exception=True)
def supplier_create(request):
    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            messages.success(request, "Supplier created successfully.")
            return redirect("purchasing:suppliers")
    else:
        form = SupplierForm()
    return render(request, "purchasing/suppliers/create.html", {"active_section": "purchasing", "form": form})


@login_required
@permission_required("purchasing.view_receipt", raise_exception=True)
def receipts_list(request):
    search = request.GET.get("q", "").strip() or None
    qs = receipts_for_list(search=search)
    page = _paginate(request, qs)
    return render(request, "purchasing/receipts/list.html", {
        "active_section": "purchasing",
        "active_purchasing": "receipts",
        "rows": page.object_list,
        "page": page,
        "search": search or "",
        "querystring": _query_wo_page(request),
    })


@login_required
@permission_required("purchasing.add_receipt", raise_exception=True)
def receive(request):
    if request.method == "POST":
        # Duplicate submission protection
        token = request.POST.get('form_token')
        if token and token == request.session.get('last_receipt_token'):
            messages.warning(request, "This exact receipt was just submitted. Ignored to prevent duplication.")
            return redirect("purchasing:receipts")

        header_form = ReceiveStockForm(request.POST)

        # Parse dynamic lines
        lines = []
        error = False
        i = 0
        while f"line_{i}_sku" in request.POST:
            line_form = ReceiveLineForm(request.POST, prefix=f"line_{i}")
            if line_form.is_valid():
                lines.append(line_form.cleaned_data)
            else:
                error = True
                messages.error(request, f"Line {i + 1} has errors.")
            i += 1

        if header_form.is_valid() and not error and lines:
            try:
                r = receive_stock(
                    supplier=header_form.cleaned_data['supplier'],
                    reference=header_form.cleaned_data['reference'],
                    user=request.user,
                    lines=lines
                )
                request.session['last_receipt_token'] = token
                messages.success(request, f"Successfully recorded receipt #{r.pk} with {len(lines)} lines.")
                return redirect("purchasing:receipts")
            except Exception as e:
                messages.error(request, f"Failed: {str(e)}")
    else:
        header_form = ReceiveStockForm()

    return render(request, "purchasing/receive.html", {
        "header_form": header_form,
        "active_section": "purchasing",
        "form_token": str(uuid.uuid4()),
    })