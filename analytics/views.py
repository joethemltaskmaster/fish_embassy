from datetime import date, timedelta
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from .metrics import (
    get_sales_summary, get_gross_profit_summary, get_stock_valuation,
    get_expiring_batches, get_low_stock_products, get_top_selling_products,
    get_weekly_report_data, get_operating_profit_summary  # <-- Add this
)


def superuser_required(view_func):
    """Decorator to ensure only is_superuser=True can access the view."""

    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("Access restricted to System Superusers.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


@superuser_required
def bi_dashboard(request):
    today = date.today()
    start_date = today - timedelta(days=30)

    context = {
        "active_section": "business_intelligence",
        "period": {
            "start": start_date.isoformat(),
            "end": today.isoformat()
        },
        "sales": get_sales_summary(start_date, today),
        "profit": get_gross_profit_summary(start_date, today),
        "operating": get_operating_profit_summary(start_date, today),  # <-- NEW
        "inventory": get_stock_valuation(),
        "top_products": get_top_selling_products(start_date, today, limit=5),
        "expiring": get_expiring_batches(days_ahead=30),
        "low_stock": get_low_stock_products()
    }
    return render(request, "analytics/dashboard.html", context)


@superuser_required
def weekly_report(request):
    """On-demand printable weekly business report."""
    context = {
        "active_section": "business_intelligence",
        "report": get_weekly_report_data()
    }
    return render(request, "analytics/weekly_report.html", context)