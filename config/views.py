"""Project-level views: dashboard, reports, administration."""

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render


@login_required
def dashboard_index(request):
    return render(request, "dashboard/index.html", {
        "active_section": "dashboard",
    })


@login_required
@permission_required("costing.view_reports", raise_exception=True)
def reports_index(request):
    return render(request, "reports/index.html", {
        "active_section": "reports",
    })


@login_required
@permission_required("auth.view_user", raise_exception=True)
def administration_index(request):
    return render(request, "administration/index.html", {
        "active_section": "administration",
    })