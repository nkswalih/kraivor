"""Tests for legacy JWT compatibility layer (jwt.py)."""

import pytest
from authentication.tokens import get_token_service


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create(
        email="jwt-test@example.com", name="JWT Test", email_verified=True
    )


@pytest.fixture
def token_service():
    return get_token_service()


@pytest.mark.django_db
class TestGenerateTokenPair:
    def test_returns_dict_with_expected_keys(self, user):
        from authentication.jwt import generate_token_pair

        result = generate_token_pair(user, "device-1", "127.0.0.1", "test")
        assert isinstance(result, dict)
        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result
        assert "expires_in" in result

    def test_tokens_are_valid(self, user):
        from authentication.jwt import generate_token_pair

        result = generate_token_pair(user, "device-1", "127.0.0.1", "test")
        token_service = get_token_service()
        payload = token_service.validate_only(result["refresh_token"])
        assert payload.user_id == str(user.id)


@pytest.mark.django_db
class TestDecodeRefreshToken:
    def test_returns_decoded_payload(self, user, token_service):
        from authentication.jwt import decode_refresh_token

        tokens = token_service.generate_tokens(user, "d", "127.0.0.1", "t")
        result = decode_refresh_token(tokens.refresh_token)
        assert isinstance(result, dict)
        assert result["user_id"] == str(user.id)
        assert result["email"] == user.email
        assert result["name"] == user.name


class TestCreateRefreshCookieDeprecated:
    def test_delegates_to_cookie_utils(self):
        from authentication.jwt import create_refresh_cookie_deprecated

        result = create_refresh_cookie_deprecated("test-token")
        assert isinstance(result, dict)
        assert result["value"] == "test-token"
        assert result["httponly"] is True
