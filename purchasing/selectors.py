from django.db.models import Count, Q
from .models import Supplier, Receipt

def suppliers_for_list(*, search: str | None = None, is_active: bool | None = None):
    qs = Supplier.objects.annotate(receipt_count=Count("receipts")).order_by("name")
    if search:
        qs = qs.filter(name__icontains=search)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs

def receipts_for_list(*, search: str | None = None, supplier_id: int | None = None):
    qs = (
        Receipt.objects
        .select_related("supplier", "received_by")
        .prefetch_related("lines")
        .order_by("-received_at", "-id")
    )
    if search:
        qs = qs.filter(Q(reference__icontains=search) | Q(supplier__name__icontains=search))
    if supplier_id:
        qs = qs.filter(supplier_id=supplier_id)
    return qs