"""
Unit and integration tests for KRV-011 sign-in flow.
"""

from unittest.mock import MagicMock, patch

import pytest
from authentication.security import reset_lockout_manager
from rest_framework.test import APIClient
from users.models import User


@pytest.mark.auth
class TestSignInIdentify:
    def setup_method(self):
        reset_lockout_manager()

    def test_identify_new_user(self, db):
        client = APIClient()
        response = client.post(
            "/api/auth/signin/identify/", {"email": "new@example.com"}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["next_step"] == "signup"

    def test_identify_locked_account(self, db):
        mock_mgr = MagicMock()
        mock_mgr.check_lockout.return_value = (True, 300)

        with (
            patch("authentication.security._lockout_manager", mock_mgr),
            patch("authentication.views.get_lockout_manager", return_value=mock_mgr),
        ):
            client = APIClient()
            response = client.post(
                "/api/auth/signin/identify/", {"email": "locked@example.com"}, format="json"
            )
            assert response.status_code == 429


@pytest.mark.auth
class TestSignInPassword:
    def setup_method(self):
        reset_lockout_manager()

    def test_valid_credentials(self, db):
        User.objects.create_user(
            email="test@example.com", password="testpass123", name="Test User", email_verified=True
        )
        client = APIClient()
        response = client.post(
            "/api/auth/signin/password/",
            {"email": "test@example.com", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_wrong_password(self, db):
        User.objects.create_user(
            email="test@example.com", password="testpass123", name="Test User", email_verified=True
        )
        client = APIClient()
        response = client.post(
            "/api/auth/signin/password/",
            {"email": "test@example.com", "password": "wrongpass"},
            format="json",
        )
        assert response.status_code == 401

    def test_locked_account(self, db):
        mock_mgr = MagicMock()
        mock_mgr.check_lockout.return_value = (True, 300)

        with (
            patch("authentication.security._lockout_manager", mock_mgr),
            patch("authentication.views.get_lockout_manager", return_value=mock_mgr),
        ):
            User.objects.create_user(
                email="test@example.com",
                password="testpass123",
                name="Test User",
                email_verified=True,
            )
            client = APIClient()
            response = client.post(
                "/api/auth/signin/password/",
                {"email": "test@example.com", "password": "testpass123"},
                format="json",
            )
            assert response.status_code == 429


@pytest.mark.auth
class TestOTPFlow:
    def setup_method(self):
        reset_lockout_manager()

    @patch("authentication.otp.get_otp_sender")
    def test_otp_send(self, mock_sender, db):
        User.objects.create_user(
            email="test@example.com", password="testpass123", name="Test User", email_verified=True
        )
        mock_sender.return_value.send = lambda e, o: None
        client = APIClient()
        response = client.post(
            "/api/auth/signin/otp/send/", {"email": "test@example.com"}, format="json"
        )
        assert response.status_code == 200

    def test_otp_verify_invalid(self, db):
        import authentication.otp as otp_module
        from authentication.otp import OTPInvalidError

        def raise_invalid(email, code):
            raise OTPInvalidError("Invalid OTP")

        mock_svc = MagicMock()
        mock_svc.verify_otp = MagicMock(side_effect=raise_invalid)

        mock_get_lockout = MagicMock()
        mock_get_lockout.check_lockout = MagicMock(return_value=(False, 0))

        User.objects.create_user(
            email="test@example.com", password="testpass123", name="Test User", email_verified=True
        )

        with patch("apps.authentication.views.get_lockout_manager", return_value=mock_get_lockout):
            otp_module._otp_service = mock_svc
            client = APIClient()
            response = client.post(
                "/api/auth/signin/otp/verify/",
                {"email": "test@example.com", "otp_code": "000000"},
                format="json",
            )
            assert response.status_code == 401


@pytest.mark.auth
class TestSignInIntegration:
    def test_full_signin_flow(self, db):
        User.objects.create_user(
            email="integration@example.com",
            password="testpass123",
            name="Test",
            email_verified=True,
        )
        client = APIClient()
        response = client.post(
            "/api/auth/signin/identify/", {"email": "integration@example.com"}, format="json"
        )
        assert response.json()["next_step"] == "choose_method"
        response = client.post(
            "/api/auth/signin/password/",
            {"email": "integration@example.com", "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["access_token"]
