"""Integration tests for API key views via APIClient."""

import pytest
from api_keys.models import APIKey
from api_keys.services.key_service import create_api_key
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create(
        email="view-test@example.com",
        name="View Tester",
        email_verified=True,
    )


@pytest.fixture
def auth_client(user):
    """APIClient authenticated as `user` via JWT."""
    from authentication.tokens import get_token_service
    client = APIClient()
    token_service = get_token_service()
    tokens = token_service.generate_tokens(user, "test-device", "127.0.0.1", "pytest")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access_token}")
    return client


@pytest.fixture
def list_create_url():
    return reverse("api-key-list-create")


@pytest.fixture
def revoke_url():
    return lambda key_id: reverse("api-key-revoke", kwargs={"key_id": str(key_id)})


@pytest.mark.django_db
class TestAPIKeyCreate:
    def test_create_returns_201_with_raw_key(self, auth_client, list_create_url):
        resp = auth_client.post(
            list_create_url,
            {"name": "CI Key", "scopes": ["analysis:read"]},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert "raw_key" in data
        assert data["raw_key"].startswith("krv_live_")
        assert data["name"] == "CI Key"

    def test_raw_key_not_in_db(self, auth_client, list_create_url):
        resp = auth_client.post(
            list_create_url,
            {"name": "Key", "scopes": ["ai:chat"]},
            format="json",
        )
        raw_key = resp.json()["raw_key"]
        assert not APIKey.objects.filter(key_hash=raw_key).exists()

    def test_invalid_scope_returns_400(self, auth_client, list_create_url):
        resp = auth_client.post(
            list_create_url,
            {"name": "Bad", "scopes": ["fake:scope"]},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated_returns_401(self, list_create_url):
        client = APIClient()
        resp = client.post(list_create_url, {"name": "Key", "scopes": ["ai:chat"]}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestAPIKeyList:
    def test_list_returns_keys(self, auth_client, user, list_create_url):
        create_api_key(user, "Key 1", ["analysis:read"])
        create_api_key(user, "Key 2", ["ai:chat"])
        resp = auth_client.get(list_create_url)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert len(data["api_keys"]) == 2

    def test_list_does_not_return_raw_key(self, auth_client, user, list_create_url):
        create_api_key(user, "Key", ["analysis:read"])
        resp = auth_client.get(list_create_url)
        for key in resp.json()["api_keys"]:
            assert "raw_key" not in key

    def test_list_excludes_revoked_keys(self, auth_client, user, list_create_url, revoke_url):
        result = create_api_key(user, "Key", ["analysis:read"])
        auth_client.delete(revoke_url(result.api_key.id))
        resp = auth_client.get(list_create_url)
        assert resp.json()["api_keys"] == []


@pytest.mark.django_db
class TestAPIKeyRevoke:
    def test_revoke_returns_200(self, auth_client, user, revoke_url):
        result = create_api_key(user, "Key", ["analysis:read"])
        resp = auth_client.delete(revoke_url(result.api_key.id))
        assert resp.status_code == status.HTTP_200_OK

    def test_revoke_sets_revoked(self, auth_client, user, revoke_url):
        result = create_api_key(user, "Key", ["analysis:read"])
        auth_client.delete(revoke_url(result.api_key.id))
        result.api_key.refresh_from_db()
        assert result.api_key.revoked is True

    def test_revoke_wrong_user_returns_404(self, user, revoke_url, django_user_model):
        """IDOR protection: cannot revoke other users' keys."""
        other = django_user_model.objects.create(
            email="other2@example.com", name="Other", email_verified=True
        )
        result = create_api_key(other, "Other's Key", ["analysis:read"])
        from authentication.tokens import get_token_service
        token_service = get_token_service()
        tokens = token_service.generate_tokens(user, "d", "127.0.0.1", "pytest")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access_token}")
        resp = client.delete(revoke_url(result.api_key.id))
        assert resp.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestAPIKeyAuthentication:
    """Test that API key Bearer tokens authenticate requests correctly."""

    def test_api_key_authenticates_request(self, user, list_create_url):
        result = create_api_key(user, "Machine Key", ["analysis:read"])
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {result.raw_key}")
        resp = client.get(list_create_url)
        assert resp.status_code == status.HTTP_200_OK

    def test_revoked_api_key_returns_401(self, user, list_create_url):
        from api_keys.services.key_service import revoke_api_key
        result = create_api_key(user, "Key", ["analysis:read"])
        revoke_api_key(user, str(result.api_key.id))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {result.raw_key}")
        resp = client.get(list_create_url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_api_key_returns_401(self, list_create_url):
        from api_keys.services.generator import generate_api_key
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {generate_api_key()[0]}")
        resp = client.get(list_create_url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jwt_still_works_alongside_api_keys(self, auth_client, list_create_url):
        """JWT auth must still work — API key backend returns None for JWTs."""
        resp = auth_client.get(list_create_url)
        assert resp.status_code == status.HTTP_200_OK