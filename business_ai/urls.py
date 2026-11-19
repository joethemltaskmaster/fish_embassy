from django.urls import path
from . import views

app_name = "business_ai"

urlpatterns = [
    path("", views.chat_interface, name="chat"),
    path("api/", views.chat_api, name="api"),
]