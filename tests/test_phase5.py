from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


def _make_user(username, group=None, superuser=False):
    user = User.objects.create_user(username=username, password="x")
    user.is_staff = superuser
    user.is_superuser = superuser
    user.save()
    if group:
        user.groups.add(Group.objects.get(name=group))
    return user


class ReportPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        cls.manager = _make_user("mgr", group="Manager")
        cls.staff = _make_user("stf", group="Inventory Staff")

    def test_staff_cannot_access_reports(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("reports_index"))
        self.assertEqual(response.status_code, 403)

    def test_staff_cannot_access_audit(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("reports_audit"))
        self.assertEqual(response.status_code, 403)

    def test_manager_can_access_reports(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("reports_index"))
        self.assertEqual(response.status_code, 200)

    def test_manager_can_access_valuation(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("reports_valuation"))
        self.assertEqual(response.status_code, 200)


class AdministrationPermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles", stdout=StringIO())
        cls.manager = _make_user("mgr", group="Manager")
        cls.superuser = _make_user("admin", superuser=True)

    def test_manager_cannot_access_administration(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("administration_index"))
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_administration(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("administration_index"))
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_create_staff(self):
        self.client.force_login(self.superuser)
        data = {
            "username": "new_staff",
            "first_name": "New",
            "last_name": "Staff",
            "email": "new@example.com",
            "password": "securepassword123",
            "group": Group.objects.get(name="Inventory Staff").pk
        }
        response = self.client.post(reverse("staff_create"), data, follow=True)
        self.assertEqual(response.status_code, 200)

        new_user = User.objects.get(username="new_staff")
        self.assertEqual(new_user.groups.first().name, "Inventory Staff")
        self.assertFalse(new_user.is_superuser)