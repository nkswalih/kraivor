"""
tests/test_api_keys.py

KRV-017 — API Key end-to-end tests.

Covers the full lifecycle:
  create → list → authenticate with key → revoke → verify revoked

Follows the exact patterns used in test_signin.py / test_github_oauth.py:
  - pytest-django with @pytest.mark.django_db
  - APIClient from rest_framework.test
  - User created via factories.py UserFactory
  - JWT access token obtained via get_token_service() (same as test_refresh_token.py)
  - reverse() for all URLs
  - No setUp classes — plain functions with fixtures
"""

from __future__ import annotations

import pytest
from api_keys.models import APIKey
from api_keys.services.generator import generate_api_key, is_api_key_format
from api_keys.services.hasher import hash_api_key, verify_api_key
from api_keys.services.key_service import (
    APIKeyExpiredError,
    APIKeyNotFoundError,
    InvalidScopeError,
    authenticate_api_key,
    create_api_key,
    revoke_api_key,
)
from authentication.tokens import get_token_service
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db, django_user_model):
    """A verified, active user — same pattern as test_signin.py."""
    return django_user_model.objects.create(
        email="apikey-user@kraivor.test",
        name="API Key Tester",
        email_verified=True,
        is_active=True,
    )


@pytest.fixture
def other_user(db, django_user_model):
    """A second user — used for IDOR / ownership tests."""
    return django_user_model.objects.create(
        email="other-user@kraivor.test",
        name="Other User",
        email_verified=True,
        is_active=True,
    )


@pytest.fixture
def jwt_client(user):
    """
    APIClient authenticated as `user` via a real JWT access token.

    Mirrors how test_signout_sessions.py obtains its auth client:
    calls get_token_service().generate_tokens() directly.
    """
    token_service = get_token_service()
    tokens = token_service.generate_tokens(user, "test-device", "127.0.0.1", "pytest/3")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access_token}")
    return client


@pytest.fixture
def list_create_url():
    return reverse("api-key-list-create")


@pytest.fixture
def revoke_url():
    return lambda key_id: reverse("api-key-revoke", kwargs={"key_id": str(key_id)})


# ─────────────────────────────────────────────────────────────────────────────
# 1. Generator
# ─────────────────────────────────────────────────────────────────────────────


def test_generate_api_key_format():
    """Raw key must match krv_live_<64hex> and is_api_key_format must accept it."""
    raw_key, prefix = generate_api_key()
    assert raw_key.startswith("krv_live_")
    rest = raw_key[len("krv_live_"):]
    assert len(rest) == 64
    assert all(c in "0123456789abcdef" for c in rest)
    assert is_api_key_format(raw_key) is True


def test_generate_api_key_prefix_stored():
    """Prefix stored in DB is a short readable identifier, not the full key."""
    raw_key, prefix = generate_api_key()
    assert prefix.startswith("krv_live_")
    assert len(prefix) < len(raw_key)  # prefix is truncated


def test_generate_api_key_is_unique():
    """100 consecutive keys must all be distinct (collision probability ≈ 0)."""
    keys = {generate_api_key()[0] for _ in range(100)}
    assert len(keys) == 100


def test_is_api_key_format_rejects_jwt():
    jwt = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
    assert is_api_key_format(jwt) is False


def test_is_api_key_format_rejects_none():
    assert is_api_key_format(None) is False  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# 2. Hasher (constant-time)
# ─────────────────────────────────────────────────────────────────────────────


def test_hash_is_64_hex_chars():
    raw_key, _ = generate_api_key()
    h = hash_api_key(raw_key)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_is_deterministic():
    raw_key, _ = generate_api_key()
    assert hash_api_key(raw_key) == hash_api_key(raw_key)


def test_verify_correct_key_passes():
    raw_key, _ = generate_api_key()
    stored = hash_api_key(raw_key)
    assert verify_api_key(raw_key, stored) is True


def test_verify_wrong_key_fails():
    raw_key, _ = generate_api_key()
    stored = hash_api_key(generate_api_key()[0])  # hash of a *different* key
    assert verify_api_key(raw_key, stored) is False


# ─────────────────────────────────────────────────────────────────────────────
# 3. Service layer — create
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_create_api_key_saves_hash_not_raw(user):
    """The DB row must contain the SHA-256 hash — never the raw key."""
    result = create_api_key(user, "CI Pipeline", ["analysis:read"])
    assert result.raw_key.startswith("krv_live_")
    # raw key is NOT in the DB
    assert not APIKey.objects.filter(key_hash=result.raw_key).exists()
    # hash IS in the DB
    expected_hash = hash_api_key(result.raw_key)
    assert APIKey.objects.filter(key_hash=expected_hash).exists()


@pytest.mark.django_db
def test_create_api_key_stores_prefix(user):
    result = create_api_key(user, "VS Code", ["ai:chat"])
    saved = APIKey.objects.get(pk=result.api_key.id)
    assert saved.prefix.startswith("krv_live_")
    assert len(saved.prefix) < len(result.raw_key)


@pytest.mark.django_db
def test_create_api_key_invalid_scope_raises(user):
    with pytest.raises(InvalidScopeError):
        create_api_key(user, "Bad Key", ["nonexistent:scope"])


@pytest.mark.django_db
def test_create_api_key_admin_scope_valid(user):
    result = create_api_key(user, "Admin Key", ["admin"])
    assert "admin" in result.api_key.scopes


@pytest.mark.django_db
def test_create_api_key_not_revoked_by_default(user):
    result = create_api_key(user, "Fresh Key", ["analysis:read"])
    assert result.api_key.revoked is False


# ─────────────────────────────────────────────────────────────────────────────
# 4. Service layer — revoke
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_revoke_sets_revoked_true(user):
    result = create_api_key(user, "To Revoke", ["analysis:read"])
    revoke_api_key(user, str(result.api_key.id))
    result.api_key.refresh_from_db()
    assert result.api_key.revoked is True


@pytest.mark.django_db
def test_revoke_wrong_user_raises(user, other_user):
    result = create_api_key(user, "Owner's Key", ["analysis:read"])
    with pytest.raises(APIKeyNotFoundError):
        revoke_api_key(other_user, str(result.api_key.id))


@pytest.mark.django_db
def test_revoke_nonexistent_key_raises(user):
    with pytest.raises(APIKeyNotFoundError):
        revoke_api_key(user, "00000000-0000-0000-0000-000000000000")


# ─────────────────────────────────────────────────────────────────────────────
# 5. Service layer — authenticate
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_authenticate_valid_key_returns_api_key(user):
    result = create_api_key(user, "Auth Key", ["analysis:read"])
    api_key = authenticate_api_key(result.raw_key)
    assert api_key.id == result.api_key.id
    assert str(api_key.user_id) == str(user.id)


@pytest.mark.django_db
def test_authenticate_unknown_key_raises(user):
    random_key, _ = generate_api_key()
    with pytest.raises(APIKeyNotFoundError):
        authenticate_api_key(random_key)


@pytest.mark.django_db
def test_authenticate_revoked_key_raises(user):
    result = create_api_key(user, "Key", ["analysis:read"])
    revoke_api_key(user, str(result.api_key.id))
    with pytest.raises(APIKeyNotFoundError):
        authenticate_api_key(result.raw_key)


@pytest.mark.django_db
def test_authenticate_expired_key_raises(user):
    from datetime import timedelta

    from django.utils import timezone

    result = create_api_key(
        user,
        "Expired",
        ["analysis:read"],
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    with pytest.raises(APIKeyExpiredError):
        authenticate_api_key(result.raw_key)


@pytest.mark.django_db
def test_authenticate_updates_last_used_at(user):
    result = create_api_key(user, "Key", ["analysis:read"])
    assert result.api_key.last_used_at is None
    authenticate_api_key(result.raw_key)
    result.api_key.refresh_from_db()
    assert result.api_key.last_used_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# 6. POST /api/auth/api-keys/  — create endpoint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_create_endpoint_returns_201_and_raw_key(jwt_client, list_create_url):
    resp = jwt_client.post(
        list_create_url,
        {"name": "GitHub Actions", "scopes": ["analysis:read"]},
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert "raw_key" in data
    assert data["raw_key"].startswith("krv_live_")
    assert "prefix" in data
    assert data["name"] == "GitHub Actions"


@pytest.mark.django_db
def test_create_endpoint_raw_key_not_in_db(jwt_client, list_create_url):
    resp = jwt_client.post(
        list_create_url,
        {"name": "CLI Tool", "scopes": ["ai:chat"]},
        format="json",
    )
    raw_key = resp.json()["raw_key"]
    assert not APIKey.objects.filter(key_hash=raw_key).exists()


@pytest.mark.django_db
def test_create_endpoint_invalid_scope_returns_400(jwt_client, list_create_url):
    resp = jwt_client.post(
        list_create_url,
        {"name": "Bad", "scopes": ["not:a:scope"]},
        format="json",
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_endpoint_unauthenticated_returns_401(list_create_url):
    client = APIClient()
    resp = client.post(
        list_create_url,
        {"name": "Key", "scopes": ["ai:chat"]},
        format="json",
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─────────────────────────────────────────────────────────────────────────────
# 7. GET /api/auth/api-keys/  — list endpoint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_list_endpoint_returns_keys(jwt_client, user, list_create_url):
    create_api_key(user, "Key 1", ["analysis:read"])
    create_api_key(user, "Key 2", ["ai:chat"])
    resp = jwt_client.get(list_create_url)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()["api_keys"]) == 2


@pytest.mark.django_db
def test_list_endpoint_never_returns_raw_key(jwt_client, user, list_create_url):
    """raw_key must NEVER appear in list responses."""
    create_api_key(user, "Key", ["analysis:read"])
    resp = jwt_client.get(list_create_url)
    for key in resp.json()["api_keys"]:
        assert "raw_key" not in key
        assert "key_hash" not in key


@pytest.mark.django_db
def test_list_endpoint_excludes_revoked_keys(jwt_client, user, list_create_url, revoke_url):
    result = create_api_key(user, "Key", ["analysis:read"])
    jwt_client.delete(revoke_url(result.api_key.id))
    resp = jwt_client.get(list_create_url)
    assert resp.json()["api_keys"] == []


@pytest.mark.django_db
def test_list_endpoint_only_shows_own_keys(user, other_user, list_create_url):
    """User A cannot see User B's keys."""
    create_api_key(other_user, "Other's Key", ["analysis:read"])
    # Authenticate as user (not other_user)
    token_service = get_token_service()
    tokens = token_service.generate_tokens(user, "dev", "127.0.0.1", "pytest/3")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access_token}")
    resp = client.get(list_create_url)
    assert resp.json()["api_keys"] == []


# ─────────────────────────────────────────────────────────────────────────────
# 8. DELETE /api/auth/api-keys/<id>/  — revoke endpoint
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_revoke_endpoint_returns_200(jwt_client, user, revoke_url):
    result = create_api_key(user, "Key", ["analysis:read"])
    resp = jwt_client.delete(revoke_url(result.api_key.id))
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_revoke_endpoint_marks_key_revoked(jwt_client, user, revoke_url):
    result = create_api_key(user, "Key", ["analysis:read"])
    jwt_client.delete(revoke_url(result.api_key.id))
    result.api_key.refresh_from_db()
    assert result.api_key.revoked is True


@pytest.mark.django_db
def test_revoke_endpoint_idor_protection(user, other_user, revoke_url):
    """Cannot revoke another user's key — must get 404, not 403."""
    result = create_api_key(other_user, "Other's Key", ["analysis:read"])
    token_service = get_token_service()
    tokens = token_service.generate_tokens(user, "dev", "127.0.0.1", "pytest/3")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access_token}")
    resp = client.delete(revoke_url(result.api_key.id))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_revoke_endpoint_nonexistent_key_returns_404(jwt_client):
    resp = jwt_client.delete(
        reverse("api-key-revoke", kwargs={"key_id": "00000000-0000-0000-0000-000000000000"})
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─────────────────────────────────────────────────────────────────────────────
# 9. API key as Bearer token (machine authentication)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_api_key_bearer_token_authenticates(user, list_create_url):
    """A raw API key in Authorization: Bearer must authenticate the request."""
    result = create_api_key(user, "Machine Key", ["analysis:read"])
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {result.raw_key}")
    resp = client.get(list_create_url)
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_revoked_api_key_bearer_returns_401(user, list_create_url):
    result = create_api_key(user, "Key", ["analysis:read"])
    revoke_api_key(user, str(result.api_key.id))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {result.raw_key}")
    resp = client.get(list_create_url)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_unknown_api_key_bearer_returns_401(list_create_url):
    random_key, _ = generate_api_key()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {random_key}")
    resp = client.get(list_create_url)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_jwt_still_works_alongside_api_keys(jwt_client, list_create_url):
    """JWT auth must continue working — API key backend must not interfere."""
    resp = jwt_client.get(list_create_url)
    assert resp.status_code == status.HTTP_200_OK


# ─────────────────────────────────────────────────────────────────────────────
# 10. model.is_valid() helper
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_model_is_valid_active_key(user):
    result = create_api_key(user, "Key", ["analysis:read"])
    assert result.api_key.is_valid() is True


@pytest.mark.django_db
def test_model_is_valid_revoked_key(user):
    result = create_api_key(user, "Key", ["analysis:read"])
    result.api_key.revoked = True
    assert result.api_key.is_valid() is False


@pytest.mark.django_db
def test_authentication_backend_expired_key_raises(user):
    """Cover the except APIKeyExpiredError branch in APIKeyAuthentication."""
    from datetime import timedelta
    from unittest.mock import MagicMock

    from api_keys.authentication.backend import APIKeyAuthentication
    from api_keys.services.key_service import create_api_key
    from django.utils import timezone

    result = create_api_key(
        user, "Exp Key", ["analysis:read"],
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    backend = APIKeyAuthentication()
    request = MagicMock()
    request.META = {"HTTP_AUTHORIZATION": f"Bearer {result.raw_key}"}
    from rest_framework.exceptions import AuthenticationFailed
    with pytest.raises(AuthenticationFailed, match="expired"):
        backend.authenticate(request)


def test_authentication_backend_no_header_returns_none():
    from unittest.mock import MagicMock

    from api_keys.authentication.backend import APIKeyAuthentication

    backend = APIKeyAuthentication()
    request = MagicMock()
    request.META = {"HTTP_AUTHORIZATION": ""}
    assert backend.authenticate(request) is None


def test_authentication_backend_bearer_only_returns_none():
    from unittest.mock import MagicMock

    from api_keys.authentication.backend import APIKeyAuthentication

    backend = APIKeyAuthentication()
    request = MagicMock()
    request.META = {"HTTP_AUTHORIZATION": "Bearer"}
    assert backend.authenticate(request) is None


def test_authentication_backend_basic_auth_returns_none():
    from unittest.mock import MagicMock

    from api_keys.authentication.backend import APIKeyAuthentication

    backend = APIKeyAuthentication()
    request = MagicMock()
    request.META = {"HTTP_AUTHORIZATION": "Basic dXNlcjpwYXNz"}
    assert backend.authenticate(request) is None


def test_authentication_backend_jwt_token_returns_none():
    from unittest.mock import MagicMock

    from api_keys.authentication.backend import APIKeyAuthentication

    backend = APIKeyAuthentication()
    request = MagicMock()
    request.META = {"HTTP_AUTHORIZATION": "Bearer eyJhbGciOiJSUzI1NiJ9.payload.sig"}
    assert backend.authenticate(request) is None


def test_authentication_backend_unexpected_error_raises():
    """Cover the except Exception branch in APIKeyAuthentication."""
    from unittest.mock import MagicMock, patch

    from api_keys.authentication.backend import APIKeyAuthentication
    from rest_framework.exceptions import AuthenticationFailed

    backend = APIKeyAuthentication()
    request = MagicMock()
    request.META = {"HTTP_AUTHORIZATION": "Bearer krv_live_" + "a" * 64}
    with (
        patch("api_keys.authentication.backend.authenticate_api_key",
              side_effect=ValueError("surprise")),
        pytest.raises(AuthenticationFailed, match="Authentication error"),
    ):
        backend.authenticate(request)


@pytest.mark.django_db
def test_model_is_valid_expired_key(user):
    from datetime import timedelta

    from django.utils import timezone

    result = create_api_key(
        user,
        "Key",
        ["analysis:read"],
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    assert result.api_key.is_valid() is False


@pytest.mark.django_db
def test_model_str(user):
    from api_keys.services.key_service import create_api_key

    result = create_api_key(user, "My Key", ["analysis:read"])
    assert str(result.api_key) == f"My Key ({user.id})"