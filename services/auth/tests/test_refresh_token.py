"""
Unit and integration tests for KRV-013: Refresh Token Rotation

Tests cover:
- Valid refresh token flow
- Expired refresh tokens
- Replay attack detection
- Concurrent refresh edge cases
- Invalid signature
- Revoked sessions
- Token rotation verification
- Session invalidation
"""

import time
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from users.models import User
from authentication.models import RefreshToken
from authentication.tokens import (
    get_token_service,
    TokenExpiredError,
    TokenInvalidError,
    TokenReusedError,
    _hash_token,
)
from authentication.cookie_utils import create_refresh_cookie


@override_settings(
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS=30,
)
class RefreshTokenRotationTests(TestCase):
    """Test suite for KRV-013 refresh token rotation."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            name="Test User",
            email_verified=True,
        )
        self.token_service = get_token_service()

    def _get_tokens_for_user(self, device_id="test-device"):
        """Helper to get tokens for a user."""
        return self.token_service.generate_tokens(
            user=self.user,
            device_id=device_id,
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

    def _set_refresh_cookie(self, response, token):
        """Helper to set refresh token cookie."""
        cookie = create_refresh_cookie(token)
        response.client.cookies['refresh_token'] = cookie['value']
        return response

    def test_valid_refresh_rotation(self):
        """Test that valid refresh token rotates properly."""
        tokens1 = self._get_tokens_for_user()

        initial_count = RefreshToken.objects.filter(user=self.user, revoked=False).count()

        response = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE=f'refresh_token={tokens1.refresh_token}',
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', response.cookies)

        final_count = RefreshToken.objects.filter(user=self.user, revoked=False).count()
        self.assertEqual(final_count, initial_count)

        revoked_count = RefreshToken.objects.filter(
            user=self.user,
            revoked=True,
        ).count()
        self.assertEqual(revoked_count, 1)

    def test_expired_refresh_token(self):
        """Test that expired refresh token is rejected."""
        tokens = self._get_tokens_for_user()
        
        token_record = RefreshToken.objects.get(
            token_hash=_hash_token(tokens.refresh_token),
            user=self.user,
        )
        token_record.expires_at = timezone.now() - timezone.timedelta(days=1)
        token_record.save()
        
        response = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE=f'refresh_token={tokens.refresh_token}',
        )
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error_code'], 'token_expired')

    def test_replay_attack_detection(self):
        """Test that reused refresh token triggers security response."""
        tokens = self._get_tokens_for_user()
        
        response1 = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE=f'refresh_token={tokens.refresh_token}',
        )
        self.assertEqual(response1.status_code, 200)
        
        response2 = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE=f'refresh_token={tokens.refresh_token}',
        )
        
        self.assertEqual(response2.status_code, 401)
        self.assertEqual(response2.json()['error_code'], 'security_alert')
        
        active_sessions = RefreshToken.objects.filter(
            user=self.user,
            revoked=False,
        ).count()
        self.assertEqual(active_sessions, 0)

    def test_invalid_signature(self):
        """Test that token with invalid signature is rejected."""
        response = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE='refresh_token=invalid.signature.token',
        )
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error_code'], 'invalid_token')

    def test_missing_refresh_token(self):
        """Test that request without refresh token is rejected."""
        response = self.client.post('/api/auth/refresh/')
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error_code'], 'missing_token')

    def test_revoked_token(self):
        """Test that revoked token triggers security alert (replay attack detected)."""
        tokens = self._get_tokens_for_user()

        token_record = RefreshToken.objects.get(
            token_hash=_hash_token(tokens.refresh_token),
            user=self.user,
        )
        token_record.revoked = True
        token_record.save()

        response = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE=f'refresh_token={tokens.refresh_token}',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error_code'], 'security_alert')

        active_sessions = RefreshToken.objects.filter(
            user=self.user,
            revoked=False,
        ).count()
        self.assertEqual(active_sessions, 0)

    def test_user_not_found(self):
        """Test that token for deleted user is rejected."""
        tokens = self._get_tokens_for_user()
        
        self.user.is_active = False
        self.user.save()
        
        response = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE=f'refresh_token={tokens.refresh_token}',
        )
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['error_code'], 'invalid_token')

    def test_token_rotation_changes_token_value(self):
        """Test that rotated token has different value."""
        tokens1 = self._get_tokens_for_user()
        
        response = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE=f'refresh_token={tokens1.refresh_token}',
        )
        
        new_token = response.cookies.get('refresh_token').value
        
        self.assertNotEqual(tokens1.refresh_token, new_token)

    def test_multiple_sessions_refresh_one(self):
        """Test that refreshing one token doesn't affect others."""
        tokens1 = self._get_tokens_for_user("device-1")
        tokens2 = self._get_tokens_for_user("device-2")

        response1 = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE=f'refresh_token={tokens1.refresh_token}',
        )

        self.assertEqual(response1.status_code, 200)

        active_sessions = RefreshToken.objects.filter(
            user=self.user,
            revoked=False,
        ).count()

        self.assertEqual(active_sessions, 2)

    def test_concurrent_refresh_same_token(self):
        """Test concurrent refresh attempts with same token."""
        tokens = self._get_tokens_for_user()
        
        response1 = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE=f'refresh_token={tokens.refresh_token}',
        )
        
        response2 = self.client.post(
            '/api/auth/refresh/',
            HTTP_COOKIE=f'refresh_token={tokens.refresh_token}',
        )
        
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 401)
        self.assertEqual(response2.json()['error_code'], 'security_alert')

    def test_fresh_token_not_expired(self):
        """Test that newly created token is valid."""
        tokens = self._get_tokens_for_user()
        
        token_record = RefreshToken.objects.get(
            token_hash=_hash_token(tokens.refresh_token),
            user=self.user,
        )
        
        self.assertTrue(token_record.is_valid())
        self.assertGreater(token_record.expires_at, timezone.now())


@override_settings(
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS=30,
)
class TokenServiceTests(TestCase):
    """Direct tests for TokenService methods."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="service@example.com",
            password="testpass123",
            name="Service Test",
            email_verified=True,
        )
        self.token_service = get_token_service()

    def test_generate_tokens_returns_pair(self):
        """Test token generation returns both access and refresh."""
        tokens = self.token_service.generate_tokens(
            user=self.user,
            device_id="test-device",
            ip_address="127.0.0.1",
        )
        
        self.assertTrue(tokens.access_token)
        self.assertTrue(tokens.refresh_token)
        self.assertEqual(tokens.token_type, "Bearer")
        self.assertEqual(tokens.expires_in, 900)

    def test_token_is_stored_in_db(self):
        """Test that generated token is stored in database."""
        tokens = self.token_service.generate_tokens(
            user=self.user,
            device_id="db-test-device",
        )
        
        stored = RefreshToken.objects.filter(
            user=self.user,
            token_hash=_hash_token(tokens.refresh_token),
        )
        
        self.assertTrue(stored.exists())

    def test_revoke_all_sessions(self):
        """Test revoking all user sessions."""
        self.token_service.generate_tokens(self.user, "device-1")
        self.token_service.generate_tokens(self.user, "device-2")
        
        count = self.token_service.revoke_all_user_tokens(self.user)
        
        self.assertEqual(count, 2)
        
        active = RefreshToken.objects.filter(
            user=self.user,
            revoked=False,
        ).count()
        self.assertEqual(active, 0)

    def test_get_active_sessions(self):
        """Test retrieving active sessions for a user."""
        self.token_service.generate_tokens(self.user, "session-1")
        self.token_service.generate_tokens(self.user, "session-2")
        
        sessions = self.token_service.get_active_sessions(self.user)
        
        self.assertEqual(len(sessions), 2)

    def test_validate_and_rotate_returns_new_tokens(self):
        """Test validate_and_rotate returns new token pair."""
        tokens1 = self.token_service.generate_tokens(
            self.user,
            device_id="rotate-test",
        )
        
        user, tokens2 = self.token_service.validate_and_rotate(
            tokens1.refresh_token,
            ip_address="127.0.0.1",
        )
        
        self.assertEqual(user, self.user)
        self.assertNotEqual(tokens1.refresh_token, tokens2.refresh_token)

    def test_validate_only_without_rotation(self):
        """Test token validation without rotation."""
        tokens = self.token_service.generate_tokens(
            self.user,
            device_id="validate-test",
        )
        
        payload = self.token_service.validate_only(tokens.refresh_token)
        
        self.assertEqual(payload.user_id, str(self.user.id))
        self.assertEqual(payload.email, self.user.email)
        self.assertEqual(payload.name, self.user.name)

    def test_hash_token_is_deterministic(self):
        """Test that token hashing is deterministic."""
        token = "test-token-value"
        
        hash1 = _hash_token(token)
        hash2 = _hash_token(token)
        
        self.assertEqual(hash1, hash2)

    def test_different_tokens_different_hashes(self):
        """Test that different tokens produce different hashes."""
        hash1 = _hash_token("token-1")
        hash2 = _hash_token("token-2")
        
        self.assertNotEqual(hash1, hash2)


@override_settings(
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS=30,
)
class LogoutTests(TestCase):
    """Test logout functionality."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="logout@example.com",
            password="testpass123",
            name="Logout Test",
            email_verified=True,
        )
        self.token_service = get_token_service()

    def test_single_logout(self):
        """Test logging out from single device."""
        tokens = self.token_service.generate_tokens(
            self.user,
            device_id="logout-device",
        )
        
        response = self.client.post(
            '/api/auth/logout/',
            HTTP_COOKIE=f'refresh_token={tokens.refresh_token}',
        )
        
        self.assertEqual(response.status_code, 200)
        
        is_revoked = not RefreshToken.objects.filter(
            user=self.user,
            token_hash=_hash_token(tokens.refresh_token),
            revoked=False,
        ).exists()
        
        self.assertTrue(is_revoked)

    def test_logout_all_devices(self):
        """Test logging out from all devices."""
        self.token_service.generate_tokens(self.user, "device-1")
        self.token_service.generate_tokens(self.user, "device-2")
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post('/api/auth/logout/all/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['sessions_revoked'], 2)
        
        active = RefreshToken.objects.filter(
            user=self.user,
            revoked=False,
        ).count()
        self.assertEqual(active, 0)


@override_settings(
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS=30,
)
class CookieSecurityTests(TestCase):
    """Test cookie security settings."""

    def test_refresh_cookie_has_security_settings(self):
        """Test that refresh cookie has proper security settings."""
        from django.conf import settings
        
        cookie = create_refresh_cookie("test-token")
        
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['path'], settings.COOKIE_PATH)
        
        if settings.COOKIE_SECURE:
            self.assertTrue(cookie['secure'])
        
        if settings.COOKIE_DOMAIN:
            self.assertEqual(cookie['domain'], settings.COOKIE_DOMAIN)