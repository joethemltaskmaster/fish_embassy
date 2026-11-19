from django.urls import path
from . import views

app_name = "purchasing"

urlpatterns = [
    path("", views.index, name="index"),
    path("suppliers/", views.suppliers_list, name="suppliers"),
    path("receipts/", views.receipts_list, name="receipts"),
    path("receive/", views.receive, name="receive"),
    path("suppliers/create/", views.supplier_create, name="supplier_create"),
]