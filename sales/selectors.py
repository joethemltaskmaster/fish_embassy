from django.db.models import Count, Q
from .models import Customer, Sale

def customers_for_list(*, search: str | None = None):
    qs = Customer.objects.annotate(sale_count=Count("sales")).order_by("name")
    if search:
        qs = qs.filter(name__icontains=search)
    return qs

def sales_for_list(*, search: str | None = None):
    qs = (
        Sale.objects
        .select_related("customer", "sold_by")
        .prefetch_related("lines__sku")
        .order_by("-occurred_at", "-id")
    )
    if search:
        qs = qs.filter(
            Q(customer__name__icontains=search) |
            Q(reference__icontains=search)
        )
    return qs