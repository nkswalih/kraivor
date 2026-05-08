from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import User


class SignUpTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.signup_url = "/api/auth/signup/"

    @patch("users.views.email_service")
    def test_valid_signup(self, mock_email):
        data = {
            "email": "test@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
            "name": "Test User",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email="test@example.com").exists())
        user = User.objects.get(email="test@example.com")
        self.assertFalse(user.email_verified)
        mock_email.send_verification_email.assert_called_once()

    @patch("users.views.email_service")
    def test_duplicate_email(self, mock_email):
        User.objects.create(email="existing@example.com", name="Existing")
        data = {
            "email": "existing@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
            "name": "Test User",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())

    @patch("users.views.email_service")
    def test_invalid_password_short(self, mock_email):
        data = {
            "email": "test@example.com",
            "password": "short",
            "password_confirm": "short",
            "name": "Test User",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json())

    @patch("users.views.email_service")
    def test_invalid_email(self, mock_email):
        data = {
            "email": "notanemail",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
            "name": "Test User",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())


class SignUpIntegrationTest(TestCase):
    @patch("users.views.email_service")
    def test_full_signup_flow(self, mock_email):
        """Integration test for full signup flow — KRV-009.
        Email verification continuation tested in test_email_verification.py (KRV-010).
        """
        client = APIClient()
        data = {
            "email": "integration@test.com",
            "password": "integrationpass123",
            "password_confirm": "integrationpass123",
            "name": "Integration Test",
        }
        response = client.post("/api/auth/signup/", data)
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="integration@test.com")
        # No longer stores token in DB — JWT is stateless (KRV-010)
        self.assertFalse(user.email_verified)
        mock_email.send_verification_email.assert_called_once()