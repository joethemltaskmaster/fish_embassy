from django.contrib import admin
from django.urls import include, path
from . import auth_views, views as config_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.ProjectLoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.ProjectLogoutView.as_view(), name="logout"),

    # Six primary sections
    path("", config_views.dashboard_index, name="dashboard_index"),
    path("inventory/", include("inventory.urls")),
    path("purchasing/", include("purchasing.urls")),
    path("sales/", include("sales.urls")),
    path("reports/", config_views.reports_index, name="reports_index"),
    path("reports/valuation/", config_views.report_valuation, name="reports_valuation"),
    path("reports/sales/", config_views.report_sales, name="reports_sales"),
    path("reports/expiry/", config_views.report_expiry, name="reports_expiry"),
    path("reports/audit/", config_views.report_audit, name="reports_audit"),
    path("administration/", config_views.administration_index, name="administration_index"),
    path("administration/create/", config_views.staff_create, name="staff_create"),
    path("administration/toggle/<int:user_id>/", config_views.staff_toggle, name="staff_toggle"),

    # NEW: Business Intelligence
    path("business-intelligence/", include("analytics.urls")),
    path("costing/", include("costing.urls")),
    path("business-intelligence/", include("analytics.urls")),
    path("business-intelligence/chat/", include("business_ai.urls")),  # <-- NEW
]