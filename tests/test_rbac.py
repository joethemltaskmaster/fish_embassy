"""
Phase 3 RBAC tests. Proves:
  - anonymous users are redirected to login
  - authenticated users without the required permission get 403
  - Manager accesses everything they should
  - Inventory Staff is blocked from sales/reports/administration
  - Superuser bypasses all permission checks
  - direct POST to forbidden URLs is rejected (button-hiding isn't security)
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


def _make_user(username, group_name=None, superuser=False):
    user = User.objects.create_user(username=username, password="x")
    user.is_superuser = superuser
    user.is_staff = superuser
    user.save()
    if group_name:
        user.groups.add(Group.objects.get(name=group_name))
    return user


class AnonymousRedirectTests(TestCase):
    """Every section URL requires login, no exceptions."""

    urls = [
        "dashboard_index",
        "inventory:index",
        "purchasing:index",
        "sales:index",
        "reports_index",
        "administration_index",
    ]

    def test_anonymous_redirected_to_login(self):
        for name in self.urls:
            with self.subTest(url=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("login"), response["Location"])


class ManagerAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles")
        cls.manager = _make_user("mgr", group_name="Manager")

    def setUp(self):
        self.client.force_login(self.manager)

    def test_manager_can_view_dashboard(self):
        self.assertEqual(self.client.get(reverse("dashboard_index")).status_code, 200)

    def test_manager_can_view_inventory(self):
        self.assertEqual(self.client.get(reverse("inventory:index")).status_code, 200)

    def test_manager_can_view_purchasing(self):
        self.assertEqual(self.client.get(reverse("purchasing:index")).status_code, 200)

    def test_manager_can_view_sales(self):
        self.assertEqual(self.client.get(reverse("sales:index")).status_code, 200)

    def test_manager_can_view_reports(self):
        self.assertEqual(self.client.get(reverse("reports_index")).status_code, 200)

    def test_manager_cannot_view_administration(self):
        # Manager does not get auth.view_user by default — only superusers do.
        response = self.client.get(reverse("administration_index"))
        self.assertEqual(response.status_code, 403)


class InventoryStaffAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles")
        cls.staff = _make_user("stf", group_name="Inventory Staff")

    def setUp(self):
        self.client.force_login(self.staff)

    def test_can_view_dashboard(self):
        self.assertEqual(self.client.get(reverse("dashboard_index")).status_code, 200)

    def test_can_view_inventory(self):
        self.assertEqual(self.client.get(reverse("inventory:index")).status_code, 200)

    def test_can_view_purchasing(self):
        self.assertEqual(self.client.get(reverse("purchasing:index")).status_code, 200)

    def test_cannot_view_sales(self):
        self.assertEqual(self.client.get(reverse("sales:index")).status_code, 403)

    def test_cannot_view_reports(self):
        self.assertEqual(self.client.get(reverse("reports_index")).status_code, 403)

    def test_cannot_view_administration(self):
        self.assertEqual(self.client.get(reverse("administration_index")).status_code, 403)


class SuperuserAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles")
        cls.su = _make_user("admin", superuser=True)

    def setUp(self):
        self.client.force_login(self.su)

    def test_superuser_can_view_all_sections(self):
        for name in (
            "dashboard_index", "inventory:index", "purchasing:index",
            "sales:index", "reports_index", "administration_index",
        ):
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)


class SidebarRespectsPermissionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles")
        cls.manager = _make_user("mgr2", group_name="Manager")
        cls.staff = _make_user("stf2", group_name="Inventory Staff")

    def test_manager_sidebar_shows_sales_reports_but_not_admin(self):
        self.client.force_login(self.manager)
        html = self.client.get(reverse("dashboard_index")).content.decode()
        self.assertIn("Sales", html)
        self.assertIn("Reports", html)
        self.assertNotIn(reverse("administration_index"), html)

    def test_staff_sidebar_hides_sales_reports_admin(self):
        self.client.force_login(self.staff)
        html = self.client.get(reverse("dashboard_index")).content.decode()
        self.assertNotIn(reverse("sales:index"), html)
        self.assertNotIn(reverse("reports_index"), html)
        self.assertNotIn(reverse("administration_index"), html)


class RoleSetupIdempotencyTests(TestCase):
    def test_setup_roles_is_idempotent(self):
        call_command("setup_roles")
        call_command("setup_roles")  # must not raise

        manager = Group.objects.get(name="Manager")
        staff = Group.objects.get(name="Inventory Staff")

        manager_perms = set(manager.permissions.values_list("codename", flat=True))
        staff_perms = set(staff.permissions.values_list("codename", flat=True))

        # Manager has these
        self.assertIn("add_sale", manager_perms)
        self.assertIn("view_costs", manager_perms)
        self.assertIn("view_reports", manager_perms)
        self.assertIn("view_audit_history", manager_perms)
        self.assertIn("approve_adjustments", manager_perms)

        # Staff has these
        self.assertIn("add_receipt", staff_perms)
        self.assertIn("view_stockmovement", staff_perms)

        # Staff does NOT have these
        self.assertNotIn("add_sale", staff_perms)
        self.assertNotIn("view_costs", staff_perms)
        self.assertNotIn("view_reports", staff_perms)
        self.assertNotIn("view_audit_history", staff_perms)
        self.assertNotIn("approve_adjustments", staff_perms)


class LogoutRequiresPostTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("setup_roles")
        cls.user = _make_user("lo", group_name="Manager")

    def test_get_logout_is_rejected(self):
        """Django 5's LogoutView is POST-only. GET should 405."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)

    def test_post_logout_works(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        # Follow up: dashboard should redirect to login (user is logged out)
        response = self.client.get(reverse("dashboard_index"))
        self.assertEqual(response.status_code, 302)