"""
Unit and integration tests for signup flow.
"""

import uuid
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient
from users.models import User


@pytest.mark.auth
class TestSignUp:
    @patch("users.views.email_service")
    def test_valid_signup(self, mock_email, db):
        client = APIClient()
        # Generate a unique email
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        data = {
            "email": unique_email,
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "name": "Test User",
        }
        response = client.post("/api/auth/signup/", data, format="json")
        assert response.status_code == 201
        assert User.objects.filter(email=unique_email).exists()
        user = User.objects.get(email=unique_email)
        assert not user.email_verified
        mock_email.send_verification_email.assert_called_once()

    @patch("users.views.email_service")
    def test_duplicate_email(self, mock_email, db):
        User.objects.create(email="existing@example.com", name="Existing")
        client = APIClient()
        data = {
            "email": "existing@example.com",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
            "name": "Test User",
        }
        response = client.post("/api/auth/signup/", data, format="json")
        assert response.status_code == 400
        assert "email" in response.json()

    @patch("users.views.email_service")
    def test_invalid_password_short(self, mock_email, db):
        client = APIClient()
        data = {
            "email": "test@example.com",
            "password": "short",
            "password_confirm": "short",
            "name": "Test User",
        }
        response = client.post("/api/auth/signup/", data, format="json")
        assert response.status_code == 400
        assert "password" in response.json()

    @patch("users.views.email_service")
    def test_invalid_email(self, mock_email, db):
        client = APIClient()
        data = {
            "email": "notanemail",
            "password": "securepassword123",
            "password_confirm": "securepassword123",
            "name": "Test User",
        }
        response = client.post("/api/auth/signup/", data, format="json")
        assert response.status_code == 400
        assert "email" in response.json()


@pytest.mark.auth
class TestSignUpIntegration:
    @patch("users.views.email_service")
    def test_full_signup_flow(self, mock_email, db):
        """Integration test for full signup flow — KRV-009."""
        client = APIClient()
        data = {
            "email": "integration@test.com",
            "password": "integrationpass123",
            "password_confirm": "integrationpass123",
            "name": "Integration Test",
        }
        response = client.post("/api/auth/signup/", data, format="json")
        assert response.status_code == 201
        user = User.objects.get(email="integration@test.com")
        assert not user.email_verified
        mock_email.send_verification_email.assert_called_once()
