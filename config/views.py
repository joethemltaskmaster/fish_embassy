from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect

from django.core.exceptions import PermissionDenied

from .forms import StaffCreationForm
from .selectors import (
    get_dashboard_metrics, get_recent_activity,
    get_valuation_report, get_sales_performance_report,
    get_expiry_report, get_audit_logs
)

User = get_user_model()

# ─── DASHBOARD ───
@login_required
def dashboard_index(request):
    metrics = get_dashboard_metrics(request.user)
    recent_activity = get_recent_activity()

    return render(request, "dashboard/index.html", {
        "active_section": "dashboard",
        "metrics": metrics,
        "recent_activity": recent_activity,
        "can_view_costs": request.user.has_perm("costing.view_costs"),
        "can_view_sales": request.user.has_perm("sales.view_sale"),
    })

# ─── REPORTS ───
@login_required
@permission_required("costing.view_reports", raise_exception=True)
def reports_index(request):
    return render(request, "reports/index.html", {"active_section": "reports"})

@login_required
@permission_required("costing.view_costs", raise_exception=True)
def report_valuation(request):
    return render(request, "reports/valuation.html", {
        "active_section": "reports",
        "rows": get_valuation_report(),
    })

@login_required
@permission_required("costing.view_reports", raise_exception=True)
def report_sales(request):
    return render(request, "reports/sales.html", {
        "active_section": "reports",
        "rows": get_sales_performance_report(),
    })

@login_required
@permission_required("inventory.view_batch", raise_exception=True)
def report_expiry(request):
    return render(request, "reports/expiry.html", {
        "active_section": "reports",
        "rows": get_expiry_report(),
    })

@login_required
@permission_required("audit.view_audit_history", raise_exception=True)
def report_audit(request):
    return render(request, "reports/audit.html", {
        "active_section": "reports",
        "rows": get_audit_logs(),
    })

# ─── ADMINISTRATION ───
@login_required
@permission_required("auth.view_user", raise_exception=True)
def administration_index(request):
    # THIS is the line that was likely missing. It fetches ALL users.
    users = User.objects.prefetch_related("groups").order_by("username")
    return render(request, "administration/index.html", {
        "active_section": "administration",
        "users": users,
    })


@login_required
@permission_required("auth.add_user", raise_exception=True)
def staff_create(request):
    if request.method == "POST":
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            # SECURITY CHECK: Only existing superusers can create new superusers
            if form.cleaned_data.get("is_superuser") and not request.user.is_superuser:
                raise PermissionDenied("Only system superusers can grant superuser status.")

            user = form.save()

            # Audit the action
            from audit.services import record
            record(
                action="staff_create",
                target=f"User {user.username}",
                payload={"is_superuser": user.is_superuser,
                         "group": form.cleaned_data['group'].name if form.cleaned_data['group'] else None}
            )

            messages.success(request, "Staff account created successfully.")
            return redirect("administration_index")
    else:
        form = StaffCreationForm()

    return render(request, "administration/create.html", {"active_section": "administration", "form": form})

@login_required
@permission_required("auth.change_user", raise_exception=True)
def staff_toggle(request, user_id):
    if request.method != "POST":
        return redirect("administration_index")

    target = User.objects.get(pk=user_id)
    if target == request.user:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("administration_index")

    target.is_active = not target.is_active
    target.save()
    status = "activated" if target.is_active else "deactivated"
    messages.success(request, f"User {target.username} {status}.")
    return redirect("administration_index")