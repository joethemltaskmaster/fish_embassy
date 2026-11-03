"""
Project-level auth views. Delegates to Django's stock LoginView/LogoutView
with our own template and redirect targets. No custom auth logic — Django's
session handling and CSRF protection are the point.
"""
from django.contrib.auth import views as auth_views


class ProjectLoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


class ProjectLogoutView(auth_views.LogoutView):
    # POST-only by default in Django 5.0+; csrf_token required in form.
    pass