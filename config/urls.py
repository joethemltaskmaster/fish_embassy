from django.contrib import admin
from django.urls import include, path

from . import auth_views, views as config_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth
    path("accounts/login/", auth_views.ProjectLoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.ProjectLogoutView.as_view(), name="logout"),

    # Six primary sections
    path("", config_views.dashboard_index, name="dashboard_index"),
    path("inventory/", include("inventory.urls")),
    path("purchasing/", include("purchasing.urls")),
    path("sales/", include("sales.urls")),
    path("reports/", config_views.reports_index, name="reports_index"),
    path("administration/", config_views.administration_index,
         name="administration_index"),
]