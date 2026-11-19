from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.index, name="index"),
    path("products/", views.products_list, name="products"),
    path("skus/", views.skus_list, name="skus"),
    path("balances/", views.balances_list, name="balances"),
    path("batches/", views.batches_list, name="batches"),
    path("locations/", views.locations_list, name="locations"),
    path("movements/", views.movements_list, name="movements"),
    path("products/create/", views.product_create, name="product_create"),
    path("skus/create/", views.sku_create, name="sku_create"),
    path("locations/create/", views.location_create, name="location_create"),
]