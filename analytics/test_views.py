from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class BusinessIntelligenceSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())

        cls.superuser = User.objects.create_superuser(username="super", password="x")
        cls.manager = User.objects.create_user(username="mgr", password="x")
        cls.manager.groups.add(Group.objects.get(name="Manager"))

        cls.staff = User.objects.create_user(username="stf", password="x")
        cls.staff.groups.add(Group.objects.get(name="Inventory Staff"))

    def test_superuser_can_access_bi_dashboard(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "analytics/dashboard.html")

    def test_superuser_can_access_weekly_report(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("analytics:weekly_report"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "analytics/weekly_report.html")

    def test_manager_cannot_access_bi_dashboard(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_staff_cannot_access_weekly_report(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("analytics:weekly_report"))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(response.status_code, 302)