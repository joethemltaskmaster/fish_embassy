from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.bi_dashboard, name="dashboard"),
    path("weekly-report/", views.weekly_report, name="weekly_report"),
]