"""
authentication/tests/test_google_oauth.py

Production-grade Google OAuth tests for Kraivor Identity Service.
"""

from unittest.mock import MagicMock, patch

import pytest
from authentication.oauth.base import OAuthUserInfo
from django.urls import reverse
from rest_framework.test import APIClient

VALID_CLAIMS = {
    "sub": "google-sub-123456",
    "email": "testuser@gmail.com",
    "email_verified": True,
    "name": "Test User",
    "picture": "https://lh3.googleusercontent.com/photo.jpg",
    "iss": "https://accounts.google.com",
    "aud": "test-client-id.apps.googleusercontent.com",
}


MOCK_TOKENS_RESPONSE = {
    "id_token": "mock.id.token",
    "access_token": "mock-access-token",
    "refresh_token": "mock-refresh-token",
    "expires_in": 3599,
    "token_type": "Bearer",
}


MOCK_USER_INFO = OAuthUserInfo(
    provider="google",
    provider_user_id="google-sub-999",
    email="test@gmail.com",
    name="Test User",
    avatar_url="https://lh3.googleusercontent.com/photo.jpg",
    email_verified=True,
    raw={"sub": "google-sub-999", "email": "test@gmail.com"},
)


# =========================================================
# Fixtures
# =========================================================


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def initiate_url():
    return reverse("google-oauth-initiate")


@pytest.fixture
def callback_url():
    return reverse("google-oauth-callback")


@pytest.fixture(autouse=True)
def patch_google_client_id(settings):
    settings.GOOGLE_CLIENT_ID = "test-client-id.apps.googleusercontent.com"


@pytest.fixture
def verifier():
    from authentication.oauth.google.services.verifier import GoogleIDTokenVerifier

    return GoogleIDTokenVerifier()


# =========================================================
# State Service Tests
# =========================================================


class TestGoogleStateService:
    @patch("authentication.oauth.google.services.state.redis.Redis")
    def test_generate_returns_hex_string(self, mock_redis):
        from authentication.oauth.google.services.state import GoogleStateService

        redis_instance = MagicMock()
        mock_redis.return_value = redis_instance

        service = GoogleStateService(redis_client=redis_instance)

        state = service.generate()

        assert len(state) == 64
        assert state.isalnum()

    @patch("authentication.oauth.google.services.state.redis.Redis")
    def test_generate_stores_in_redis(self, mock_redis):
        from authentication.oauth.google.services.state import GoogleStateService

        redis_instance = MagicMock()
        mock_redis.return_value = redis_instance

        service = GoogleStateService(redis_client=redis_instance)

        state = service.generate()

        redis_instance.setex.assert_called_once()

        args = redis_instance.setex.call_args[0]
        assert state in args[0]

    @patch("authentication.oauth.google.services.state.redis.Redis")
    def test_replay_attack_second_consume_fails(self, mock_redis):
        from authentication.oauth.google.services.state import GoogleStateService

        redis_instance = MagicMock()
        redis_instance.delete.side_effect = [1, 0]

        service = GoogleStateService(redis_client=redis_instance)

        assert service.consume("abc123") is True
        assert service.consume("abc123") is False


# =========================================================
# Verifier Tests
# =========================================================


class TestGoogleIDTokenVerifier:
    @patch("authentication.oauth.google.services.verifier.google_id_token.verify_oauth2_token")
    def test_valid_token_returns_user_info(self, mock_verify, verifier):
        mock_verify.return_value = VALID_CLAIMS

        user_info = verifier.verify({"id_token": "valid.jwt.token"})

        assert user_info.provider == "google"
        assert user_info.provider_user_id == "google-sub-123456"
        assert user_info.email == "testuser@gmail.com"

    @patch("authentication.oauth.google.services.verifier.google_id_token.verify_oauth2_token")
    def test_unverified_email_raises(self, mock_verify, verifier):
        from authentication.oauth.google.services.verifier import (
            GoogleIDTokenVerificationError,
        )

        claims = {**VALID_CLAIMS, "email_verified": False}

        mock_verify.return_value = claims

        with pytest.raises(GoogleIDTokenVerificationError):
            verifier.verify({"id_token": "jwt"})

    @patch("authentication.oauth.google.services.verifier.google_id_token.verify_oauth2_token")
    def test_invalid_issuer_raises(self, mock_verify, verifier):
        from authentication.oauth.google.services.verifier import (
            GoogleIDTokenVerificationError,
        )

        claims = {**VALID_CLAIMS, "iss": "https://evil.com"}

        mock_verify.return_value = claims

        with pytest.raises(GoogleIDTokenVerificationError):
            verifier.verify({"id_token": "jwt"})

    def test_missing_id_token_raises(self, verifier):
        from authentication.oauth.google.services.verifier import (
            GoogleIDTokenVerificationError,
        )

        with pytest.raises(GoogleIDTokenVerificationError):
            verifier.verify({"access_token": "only"})


# =========================================================
# OAuth Initiate View
# =========================================================


class TestGoogleOAuthInitiateView:
    @patch("authentication.oauth.google.views.GoogleStateService")
    def test_redirect_to_google(self, MockStateService, client, initiate_url):
        MockStateService.return_value.generate.return_value = "teststate123"

        response = client.get(initiate_url)

        assert response.status_code == 302
        assert "accounts.google.com" in response["Location"]
        assert "openid" in response["Location"]
        assert "email" in response["Location"]
        assert "teststate123" in response["Location"]

    @patch("authentication.oauth.google.views.GoogleStateService")
    def test_redis_failure_returns_503(self, MockStateService, client, initiate_url):
        MockStateService.return_value.generate.side_effect = RuntimeError("Redis down")

        response = client.get(initiate_url)

        assert response.status_code == 503


# =========================================================
# OAuth Callback View
# =========================================================


class TestGoogleOAuthCallbackView:
    @pytest.mark.django_db
    @patch("authentication.oauth.google.views.get_token_service")
    @patch("authentication.oauth.google.views.GoogleIdentityService")
    @patch("authentication.oauth.google.views.GoogleIDTokenVerifier")
    @patch("authentication.oauth.google.views.GoogleTokenExchanger")
    @patch("authentication.oauth.google.views.GoogleStateService")
    def test_successful_new_user_login(
        self,
        MockState,
        MockExchanger,
        MockVerifier,
        MockIdentity,
        MockTokenService,
        client,
        callback_url,
    ):
        MockState.return_value.consume.return_value = True

        MockExchanger.return_value.exchange.return_value = MOCK_TOKENS_RESPONSE

        MockVerifier.return_value.verify.return_value = MOCK_USER_INFO

        mock_user = MagicMock()
        mock_user.id = "uuid-123"
        mock_user.email = "test@gmail.com"
        mock_user.name = "Test User"

        MockIdentity.return_value.get_or_create.return_value = (
            mock_user,
            True,
        )

        mock_tokens = MagicMock()
        mock_tokens.access_token = "kraivor.access.token"
        mock_tokens.refresh_token = "kraivor.refresh.token"
        mock_tokens.token_type = "Bearer"
        mock_tokens.expires_in = 900

        MockTokenService.return_value.generate_tokens.return_value = mock_tokens

        response = client.get(
            callback_url,
            {
                "state": "validstate",
                "code": "authcode",
            },
        )

        assert response.status_code == 302

        assert response.url.startswith(
            "http://localhost/oauth/success"
        )

        assert "access_token=" in response.url

        assert "refresh_token" in response.cookies

    @patch("authentication.oauth.google.views.GoogleStateService")
    def test_invalid_state_returns_400(
        self,
        MockState,
        client,
        callback_url,
    ):
        MockState.return_value.consume.return_value = False

        response = client.get(
            callback_url,
            {
                "state": "badstate",
                "code": "code",
            },
        )

        assert response.status_code == 400

    @patch("authentication.oauth.google.views.GoogleStateService")
    def test_missing_state_returns_400(
        self,
        MockState,
        client,
        callback_url,
    ):
        response = client.get(
            callback_url,
            {
                "code": "code",
            },
        )

        assert response.status_code == 400

    @patch("authentication.oauth.google.views.GoogleStateService")
    def test_oauth_denied_by_user(
        self,
        MockState,
        client,
        callback_url,
    ):
        response = client.get(
            callback_url,
            {
                "error": "access_denied",
            },
        )

        assert response.status_code == 400

    @patch("authentication.oauth.google.views.GoogleTokenExchanger")
    @patch("authentication.oauth.google.views.GoogleStateService")
    def test_exchange_failure_returns_502(
        self,
        MockState,
        MockExchanger,
        client,
        callback_url,
    ):
        from authentication.oauth.google.services.exchange import (
            GoogleTokenExchangeError,
        )

        MockState.return_value.consume.return_value = True

        MockExchanger.return_value.exchange.side_effect = GoogleTokenExchangeError("fail")

        response = client.get(
            callback_url,
            {
                "state": "state",
                "code": "code",
            },
        )

        assert response.status_code == 502

    @patch("authentication.oauth.google.views.GoogleIDTokenVerifier")
    @patch("authentication.oauth.google.views.GoogleTokenExchanger")
    @patch("authentication.oauth.google.views.GoogleStateService")
    def test_invalid_id_token_returns_401(
        self,
        MockState,
        MockExchanger,
        MockVerifier,
        client,
        callback_url,
    ):
        from authentication.oauth.google.services.verifier import (
            GoogleIDTokenVerificationError,
        )

        MockState.return_value.consume.return_value = True

        MockExchanger.return_value.exchange.return_value = MOCK_TOKENS_RESPONSE

        MockVerifier.return_value.verify.side_effect = GoogleIDTokenVerificationError("invalid")

        response = client.get(
            callback_url,
            {
                "state": "state",
                "code": "code",
            },
        )

        assert response.status_code == 401


# =========================================================
# Refresh Cookie Security
# =========================================================


class TestRefreshCookieSecurity:
    @pytest.mark.django_db
    @patch("authentication.oauth.google.views.get_token_service")
    @patch("authentication.oauth.google.views.GoogleIdentityService")
    @patch("authentication.oauth.google.views.GoogleIDTokenVerifier")
    @patch("authentication.oauth.google.views.GoogleTokenExchanger")
    @patch("authentication.oauth.google.views.GoogleStateService")
    def test_refresh_cookie_security_flags(
        self,
        MockState,
        MockExchanger,
        MockVerifier,
        MockIdentity,
        MockTokenService,
        client,
        callback_url,
    ):
        MockState.return_value.consume.return_value = True

        MockExchanger.return_value.exchange.return_value = MOCK_TOKENS_RESPONSE

        MockVerifier.return_value.verify.return_value = MOCK_USER_INFO

        mock_user = MagicMock()
        mock_user.id = "uuid-456"
        mock_user.email = "test@gmail.com"
        mock_user.name = "Test User"

        MockIdentity.return_value.get_or_create.return_value = (
            mock_user,
            False,
        )

        mock_tokens = MagicMock()
        mock_tokens.access_token = "access"
        mock_tokens.refresh_token = "refresh"
        mock_tokens.token_type = "Bearer"
        mock_tokens.expires_in = 900

        MockTokenService.return_value.generate_tokens.return_value = mock_tokens

        response = client.get(
            callback_url,
            {
                "state": "state",
                "code": "code",
            },
        )

        cookie = response.cookies["refresh_token"]

        assert cookie["httponly"]
