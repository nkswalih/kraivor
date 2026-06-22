"""Unit tests for APIKey service layer."""

import pytest
from api_keys.models import APIKey
from api_keys.services.generator import generate_api_key
from api_keys.services.hasher import hash_api_key
from api_keys.services.key_service import (
    APIKeyExpiredError,
    APIKeyNotFoundError,
    InvalidScopeError,
    authenticate_api_key,
    create_api_key,
    revoke_api_key,
)
from datetime import timedelta
from django.utils import timezone


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create(
        email="test@example.com",
        name="Test User",
        email_verified=True,
    )


@pytest.mark.django_db
class TestCreateAPIKey:
    def test_creates_key_with_valid_scopes(self, user):
        result = create_api_key(user, "CI Key", ["analysis:read"])
        assert result.api_key.name == "CI Key"
        assert result.api_key.scopes == ["analysis:read"]
        assert result.raw_key.startswith("krv_live_")
        # Raw key is not stored
        assert APIKey.objects.filter(key_hash=result.raw_key).count() == 0

    def test_raw_key_hashed_in_db(self, user):
        result = create_api_key(user, "CI Key", ["analysis:read"])
        expected_hash = hash_api_key(result.raw_key)
        assert APIKey.objects.filter(key_hash=expected_hash).exists()

    def test_invalid_scope_raises(self, user):
        with pytest.raises(InvalidScopeError):
            create_api_key(user, "Bad Key", ["nonexistent:scope"])

    def test_admin_scope_valid(self, user):
        result = create_api_key(user, "Admin Key", ["admin"])
        assert "admin" in result.api_key.scopes

    def test_multiple_scopes(self, user):
        result = create_api_key(user, "Multi", ["analysis:read", "ai:chat"])
        assert set(result.api_key.scopes) == {"analysis:read", "ai:chat"}

    def test_expiry_stored(self, user):
        exp = timezone.now() + timedelta(days=30)
        result = create_api_key(user, "Expiring", ["analysis:read"], expires_at=exp)
        assert result.api_key.expires_at is not None


@pytest.mark.django_db
class TestRevokeAPIKey:
    def test_revoke_sets_revoked(self, user):
        result = create_api_key(user, "To Revoke", ["analysis:read"])
        revoke_api_key(user, str(result.api_key.id))
        result.api_key.refresh_from_db()
        assert result.api_key.revoked is True

    def test_revoke_wrong_user_raises(self, user, django_user_model):
        other = django_user_model.objects.create(
            email="other@example.com", name="Other", email_verified=True
        )
        result = create_api_key(user, "Key", ["analysis:read"])
        with pytest.raises(APIKeyNotFoundError):
            revoke_api_key(other, str(result.api_key.id))

    def test_revoke_nonexistent_raises(self, user):
        with pytest.raises(APIKeyNotFoundError):
            revoke_api_key(user, "00000000-0000-0000-0000-000000000000")


@pytest.mark.django_db
class TestAuthenticateAPIKey:
    def test_valid_key_authenticates(self, user):
        result = create_api_key(user, "Auth Key", ["analysis:read"])
        api_key = authenticate_api_key(result.raw_key)
        assert api_key.id == result.api_key.id
        assert api_key.user_id == user.id

    def test_invalid_key_raises(self, user):
        with pytest.raises(APIKeyNotFoundError):
            raw_key, _ = generate_api_key()
            authenticate_api_key(raw_key)  # random, not in DB

    def test_revoked_key_raises(self, user):
        result = create_api_key(user, "Key", ["analysis:read"])
        revoke_api_key(user, str(result.api_key.id))
        with pytest.raises(APIKeyNotFoundError):
            authenticate_api_key(result.raw_key)

    def test_expired_key_raises(self, user):
        result = create_api_key(
            user, "Expired", ["analysis:read"],
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        with pytest.raises(APIKeyExpiredError):
            authenticate_api_key(result.raw_key)

    def test_updates_last_used_at(self, user):
        result = create_api_key(user, "Key", ["analysis:read"])
        assert result.api_key.last_used_at is None
        authenticate_api_key(result.raw_key)
        result.api_key.refresh_from_db()
        assert result.api_key.last_used_at is not None