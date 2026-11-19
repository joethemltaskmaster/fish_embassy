from django.urls import path
from . import views

urlpatterns = [
    path("expenses/", views.expenses_list, name="expenses_list"),
    path("expenses/create/", views.expense_create, name="expense_create"),
]