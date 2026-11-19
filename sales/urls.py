from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [
    path("", views.index, name="index"),
    path("customers/", views.customers_list, name="customers"),
    path("history/", views.sales_list, name="list"),
    path("sell/", views.sell, name="sell"),
    path("customers/create/", views.customer_create, name="customer_create"),
    path("fefo-preview/", views.fefo_preview_api, name="fefo_preview"),
]