from django.urls import path
from . import views

app_name = "purchasing"

urlpatterns = [
    path("", views.index, name="index"),
]