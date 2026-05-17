"""
GitHub OAuth Tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.authentication.oauth.github import GitHubOAuthService, GitHubUser, GitHubOAuthError
from apps.authentication.oauth.encryption import TokenEncryptionService, get_encryption_service
from apps.authentication.oauth.state_manager import OAuthStateManager
from apps.authentication.services.user_service import find_or_create_oauth_user
from apps.users.models import User
from apps.authentication.models import OAuthIdentity


@override_settings(GITHUB_CLIENT_ID="test-client-id", GITHUB_CLIENT_SECRET="test-secret", GITHUB_REDIRECT_URI="http://test.com/callback", OAUTH_TOKEN_ENCRYPTION_KEY="/tmp/test-key.key")
class TestGitHubOAuthService(TestCase):
    def setUp(self):
        self.service = GitHubOAuthService()

    def test_get_authorization_url(self):
        url = self.service.get_authorization_url("test-state")
        self.assertIn("client_id=test-client-id", url)
        self.assertIn("state=test-state", url)
        self.assertIn("github.com/login/oauth/authorize", url)

    @patch("apps.authentication.oauth.github.requests.post")
    def test_exchange_code_for_token_success(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {"access_token": "test_token_123"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        token = self.service.exchange_code_for_token("test_code")
        self.assertEqual(token, "test_token_123")

    @patch("apps.authentication.oauth.github.requests.post")
    def test_exchange_code_for_token_no_token(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        with self.assertRaises(GitHubOAuthError):
            self.service.exchange_code_for_token("test_code")

    @patch("apps.authentication.oauth.github.requests.get")
    def test_get_user_success(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"id": 123, "login": "testuser", "name": "Test User", "email": "test@example.com", "avatar_url": "http://avatar.com/123"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        user = self.service.get_user("test_token")
        self.assertEqual(user.id, 123)
        self.assertEqual(user.login, "testuser")
        self.assertEqual(user.email, "test@example.com")


class TestTokenEncryptionService(TestCase):
    def test_encrypt_decrypt(self):
        service = TokenEncryptionService()
        service._fernet = MagicMock()
        mock_fernet = service._fernet

        encrypted = service.encrypt("test-token")
        mock_fernet.encrypt.assert_called_once()

    def test_encrypt_empty_token(self):
        service = TokenEncryptionService()
        with self.assertRaises(Exception):
            service.encrypt("")

    def test_decrypt_empty_token(self):
        service = TokenEncryptionService()
        with self.assertRaises(Exception):
            service.decrypt("")


@patch("apps.authentication.oauth.state_manager.redis.from_url")
class TestOAuthStateManager(TestCase):
    def test_generate_state(self, mock_redis):
        mock_client = Mock()
        mock_redis.return_value = mock_client

        manager = OAuthStateManager()
        state = manager.generate_state("github")
        self.assertTrue(len(state) > 20)
        mock_client.setex.assert_called_once()

    def test_validate_state_valid(self, mock_redis):
        mock_client = Mock()
        mock_client.delete.return_value = 1
        mock_redis.return_value = mock_client

        manager = OAuthStateManager()
        result = manager.validate_state("github", "valid-state")
        self.assertTrue(result)

    def test_validate_state_invalid(self, mock_redis):
        mock_client = Mock()
        mock_client.delete.return_value = 0
        mock_redis.return_value = mock_client

        manager = OAuthStateManager()
        result = manager.validate_state("github", "invalid-state")
        self.assertFalse(result)


class TestUserService(TestCase):
    def test_find_or_create_oauth_user_new(self):
        user, created = find_or_create_oauth_user("github", "123456", "test@example.com", "Test User", None)
        self.assertTrue(created)
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.name, "Test User")
        identity = OAuthIdentity.objects.filter(provider="github", provider_user_id="123456").first()
        self.assertIsNotNone(identity)

    def test_find_or_create_oauth_user_existing(self):
        user1, _ = find_or_create_oauth_user("github", "123456", "test@example.com", "Test User", None)
        user2, created = find_or_create_oauth_user("github", "123456", "test2@example.com", "Different Name", None)
        self.assertFalse(created)
        self.assertEqual(user1.id, user2.id)


class TestGitHubOAuthViews(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.authentication.oauth.views.get_github_oauth_service")
    @patch("apps.authentication.oauth.views.get_state_manager")
    def test_initiate_success(self, mock_state_manager, mock_oauth_service):
        mock_manager = Mock()
        mock_manager.generate_state.return_value = "test-state"
        mock_state_manager.return_value = mock_manager

        mock_service = Mock()
        mock_service.get_authorization_url.return_value = "http://github.com/auth"
        mock_oauth_service.return_value = mock_service

        response = self.client.get("/api/auth/github/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("authorization_url", response.data)

    @patch("apps.authentication.oauth.views.get_github_oauth_service")
    @patch("apps.authentication.oauth.views.get_state_manager")
    def test_callback_invalid_state(self, mock_state_manager, mock_oauth_service):
        mock_manager = Mock()
        mock_manager.validate_state.return_value = False
        mock_state_manager.return_value = mock_manager

        response = self.client.get("/api/auth/github/callback/", {"code": "test", "state": "invalid"})
        self.assertEqual(response.status_code, 400)