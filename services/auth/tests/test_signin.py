"""
Unit and integration tests for KRV-011 sign-in flow.
"""

from unittest.mock import MagicMock, patch

import pytest
from authentication.security import reset_lockout_manager
from rest_framework.test import APIClient

from tests.factories import UserFactory


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
        user = UserFactory.verified()
        client = APIClient()
        response = client.post(
            "/api/auth/signin/password/",
            {"email": user.email, "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_wrong_password(self, db):
        user = UserFactory.verified()
        client = APIClient()
        response = client.post(
            "/api/auth/signin/password/",
            {"email": user.email, "password": "wrongpass"},
            format="json",
        )
        assert response.status_code == 401

    def test_locked_account(self, db):
        user = UserFactory.verified()
        mock_mgr = MagicMock()
        mock_mgr.check_lockout.return_value = (True, 300)

        with (
            patch("authentication.security._lockout_manager", mock_mgr),
            patch("authentication.views.get_lockout_manager", return_value=mock_mgr),
        ):
            client = APIClient()
            response = client.post(
                "/api/auth/signin/password/",
                {"email": user.email, "password": "testpass123"},
                format="json",
            )
            assert response.status_code == 429


@pytest.mark.auth
class TestOTPFlow:
    def setup_method(self):
        reset_lockout_manager()

    @patch("authentication.otp.get_otp_sender")
    def test_otp_send(self, mock_sender, db):
        user = UserFactory.verified()
        mock_sender.return_value.send = lambda e, o: None
        client = APIClient()
        response = client.post(
            "/api/auth/signin/otp/send/", {"email": user.email}, format="json"
        )
        assert response.status_code == 200

    def test_otp_verify_invalid(self, db):
        import authentication.otp as otp_module
        from authentication.otp import OTPInvalidError

        user = UserFactory.verified()

        def raise_invalid(email, code):
            raise OTPInvalidError("Invalid OTP")

        mock_svc = MagicMock()
        mock_svc.verify_otp = MagicMock(side_effect=raise_invalid)

        mock_mgr = MagicMock()
        mock_mgr.check_lockout.return_value = (False, 0)
        mock_mgr.record_failure = MagicMock()

        # FIX: patch path must match how views.py imports — "authentication.views"
        # not "apps.authentication.views" (apps/ is filesystem, not Python module path)
        with patch("authentication.views.get_lockout_manager", return_value=mock_mgr):
            otp_module._otp_service = mock_svc
            client = APIClient()
            response = client.post(
                "/api/auth/signin/otp/verify/",
                {"email": user.email, "otp_code": "000000"},
                format="json",
            )
            assert response.status_code == 401


@pytest.mark.auth
class TestSignInIntegration:
    def test_full_signin_flow(self, db):
        # FIX: use user.email in the identify step — not a hardcoded email
        # that doesn't match the created user, which returns next_step="signup"
        user = UserFactory.verified()
        client = APIClient()

        # Step 1: identify with the actual user's email
        response = client.post(
            "/api/auth/signin/identify/", {"email": user.email}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["next_step"] == "choose_method"

        # Step 2: sign in with password
        response = client.post(
            "/api/auth/signin/password/",
            {"email": user.email, "password": "testpass123"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["access_token"]