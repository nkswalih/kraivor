"""
Unit and integration tests for KRV-011 sign-in flow.
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User
from authentication.security import get_lockout_manager
from authentication.otp import get_otp_service


class SignInIdentifyTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/signin/identify/"

    def test_identify_new_user(self):
        response = self.client.post(self.url, {"email": "new@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["next_step"], "signup")

    @patch("authentication.views.get_lockout_manager")
    def test_identify_locked_account(self, mock_get_mgr):
        from authentication.security import LoginLockoutManager
        mock_mgr = LoginLockoutManager()
        mock_mgr.check_lockout = lambda e, ip: (True, 300)
        mock_get_mgr.return_value = mock_mgr
        response = self.client.post(self.url, {"email": "locked@example.com"})
        self.assertEqual(response.status_code, 429)


class SignInPasswordTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/auth/signin/password/"
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", name="Test User", email_verified=True
        )

    def test_valid_credentials(self):
        response = self.client.post(
            self.url, {"email": "test@example.com", "password": "testpass123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    def test_wrong_password(self):
        response = self.client.post(
            self.url, {"email": "test@example.com", "password": "wrongpass"}
        )
        self.assertEqual(response.status_code, 401)

    @patch("authentication.views.get_lockout_manager")
    def test_locked_account(self, mock_get_mgr):
        from authentication.security import LoginLockoutManager
        mock_mgr = LoginLockoutManager()
        mock_mgr.check_lockout = lambda e, ip: (True, 300)
        mock_get_mgr.return_value = mock_mgr
        response = self.client.post(
            self.url, {"email": "test@example.com", "password": "testpass123"}
        )
        self.assertEqual(response.status_code, 429)


class OTPFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", name="Test User", email_verified=True
        )

    @patch("authentication.otp.get_otp_sender")
    def test_otp_send(self, mock_sender):
        mock_sender.return_value.send = lambda e, o: None
        response = self.client.post("/api/auth/signin/otp/send/", {"email": "test@example.com"})
        self.assertEqual(response.status_code, 200)

    @patch("authentication.views.get_lockout_manager")
    @patch("authentication.views.get_otp_service")
    def test_otp_verify_invalid(self, mock_otp_svc, mock_lockout_mgr):
        from authentication.otp import OTPService
        from authentication.security import LoginLockoutManager
        mock_svc = OTPService()
        mock_svc.verify_otp = lambda e, c: (_ for _ in ()).throw(Exception("Invalid OTP"))
        mock_otp_svc.return_value = mock_svc
        mock_mgr = LoginLockoutManager()
        mock_mgr.check_lockout = lambda e, ip: (False, 0)
        mock_lockout_mgr.return_value = mock_mgr
        response = self.client.post(
            "/api/auth/signin/otp/verify/", {"email": "test@example.com", "otp_code": "000000"}
        )
        self.assertEqual(response.status_code, 401)


class SignInIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="integration@example.com", password="testpass123", name="Test", email_verified=True
        )

    def test_full_signin_flow(self):
        response = self.client.post("/api/auth/signin/identify/", {"email": "integration@example.com"})
        self.assertEqual(response.json()["next_step"], "choose_method")
        response = self.client.post(
            "/api/auth/signin/password/", {"email": "integration@example.com", "password": "testpass123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["access_token"])