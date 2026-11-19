from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class BusinessAIViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(username="super", password="x")
        self.staff = User.objects.create_user(username="staff", password="x")

    def test_superuser_can_access_chat_interface(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("business_ai:chat"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "business_ai/chat.html")

    def test_staff_cannot_access_chat_interface(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("business_ai:chat"))
        self.assertEqual(response.status_code, 403) # Forbidden

    def test_anonymous_redirected(self):
        response = self.client.get(reverse("business_ai:chat"))
        self.assertEqual(response.status_code, 302)