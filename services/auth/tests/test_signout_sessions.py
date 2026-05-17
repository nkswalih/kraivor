"""
KRV-014: Sign Out & Session Management — Test Suite

Place at: services/auth/tests/test_krv014_sessions.py

Run:
    pytest tests/test_krv014_sessions.py -v

Fixtures use pytest-django. Requires:
    pytest, pytest-django, factory_boy (optional)

Model assumptions (from authentication/models.py):
    RefreshToken.revoked       = BooleanField(default=False)
    RefreshToken.device_id     = CharField
    RefreshToken.expires_at    = DateTimeField
    RefreshToken.last_used_at  = DateTimeField (nullable)
    RefreshToken.token_hash    = CharField
"""

import hashlib
import uuid
from datetime import timedelta

import pytest
from authentication.models import RefreshToken
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from users.models import User

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def make_session(user, raw_token="test_raw_token", device_id=None, revoked=False, expired=False,
                 device_name="Chrome on macOS", device_type="desktop"):
    """Factory helper to create a RefreshToken row."""
    expires_at = (
        timezone.now() - timedelta(days=1)   # already expired
        if expired
        else timezone.now() + timedelta(days=30)
    )
    return RefreshToken.objects.create(
        user=user,
        token_hash=make_token_hash(raw_token),
        device_id=str(device_id or uuid.uuid4()),
        device_name=device_name,
        device_type=device_type,
        ip_address="203.0.113.1",
        user_agent="Mozilla/5.0 (Test)",
        expires_at=expires_at,
        revoked=revoked,
        last_used_at=timezone.now(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@kraivor.com",
        password="StrongPass123!",
        name="Test User",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other@kraivor.com",
        password="StrongPass123!",
        name="Other User",
    )


@pytest.fixture
def anon_client():
    return APIClient()


@pytest.fixture
def auth_client(user):
    """Authenticated client — JWT payload includes device_id."""
    client = APIClient()
    # force_authenticate bypasses JWT; device_id injected via token dict
    # so SessionListView.get_is_current works correctly in tests.
    client.force_authenticate(user=user, token={"device_id": "test-device-abc"})
    return client


@pytest.fixture
def other_client(other_user):
    client = APIClient()
    client.force_authenticate(user=other_user, token={"device_id": "other-device-xyz"})
    return client


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/auth/signout/
# ─────────────────────────────────────────────────────────────────────────────

class TestSignOut:

    def test_signout_revokes_token_and_clears_cookie(self, anon_client, user):
        """Valid refresh cookie → token set to revoked=True, cookie cleared."""
        raw = "valid_raw_token_001"
        session = make_session(user, raw_token=raw)

        anon_client.cookies["refresh_token"] = raw
        response = anon_client.post(reverse("signout"))

        assert response.status_code == 200
        assert response.data["message"] == "Signed out successfully."

        session.refresh_from_db()
        assert session.revoked is True

        # Cookie should be expired (max_age=0 or empty value)
        cookie = response.cookies.get("refresh_token")
        assert cookie is not None
        assert cookie.value == "" or cookie["max-age"] == 0

    def test_signout_no_cookie_returns_200(self, anon_client):
        """No cookie present → still 200, no crash."""
        response = anon_client.post(reverse("signout"))
        assert response.status_code == 200
        assert response.data["message"] == "Signed out successfully."

    def test_signout_invalid_cookie_value_returns_200(self, anon_client, db):
        """Garbage cookie value → 200, nothing in DB to revoke."""
        anon_client.cookies["refresh_token"] = "this_is_total_garbage_xyz"
        response = anon_client.post(reverse("signout"))
        assert response.status_code == 200

    def test_signout_already_revoked_token_returns_200(self, anon_client, user):
        """Token already revoked → still 200 (idempotent)."""
        raw = "already_revoked_token"
        make_session(user, raw_token=raw, revoked=True)

        anon_client.cookies["refresh_token"] = raw
        response = anon_client.post(reverse("signout"))
        assert response.status_code == 200

    def test_signout_does_not_revoke_other_users_sessions(self, anon_client, user, other_user):
        """
        Signing out with token A must not touch other users' sessions.
        Only the exact token hash match is revoked.
        """
        my_raw = "my_token_abc"
        their_raw = "their_token_xyz"

        make_session(user, raw_token=my_raw)
        their_session = make_session(other_user, raw_token=their_raw)

        anon_client.cookies["refresh_token"] = my_raw
        anon_client.post(reverse("signout"))

        their_session.refresh_from_db()
        assert their_session.revoked is False  # untouched

    def test_signout_does_not_require_jwt(self, anon_client, user):
        """
        No Authorization header needed — sign out works with cookie alone.
        Covers the case where access token has already expired.
        """
        raw = "token_for_no_jwt_test"
        make_session(user, raw_token=raw)
        anon_client.cookies["refresh_token"] = raw

        # Deliberately no force_authenticate / no Authorization header
        response = anon_client.post(reverse("signout"))
        assert response.status_code == 200

    def test_signout_only_revokes_matching_token(self, anon_client, user):
        """User has 2 sessions; signing out revokes only the one in the cookie."""
        raw_a = "token_session_a"
        raw_b = "token_session_b"

        session_a = make_session(user, raw_token=raw_a)
        session_b = make_session(user, raw_token=raw_b)

        anon_client.cookies["refresh_token"] = raw_a
        anon_client.post(reverse("signout"))

        session_a.refresh_from_db()
        session_b.refresh_from_db()

        assert session_a.revoked is True
        assert session_b.revoked is False


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/auth/sessions/
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionList:

    def test_returns_only_active_sessions(self, auth_client, user):
        """Revoked and expired sessions must not appear."""
        make_session(user, raw_token="active_1", device_name="Chrome on macOS")
        make_session(user, raw_token="revoked_1", revoked=True)
        make_session(user, raw_token="expired_1", expired=True)

        response = auth_client.get(reverse("session-list"))

        assert response.status_code == 200
        sessions = response.data["sessions"]
        assert len(sessions) == 1
        assert sessions[0]["device_name"] == "Chrome on macOS"

    def test_marks_current_session(self, user):
        """Session whose device_id matches JWT device_id → is_current=True."""
        device_id = str(uuid.uuid4())
        make_session(user, raw_token="curr_token", device_id=device_id)

        client = APIClient()
        client.force_authenticate(user=user, token={"device_id": device_id})

        response = client.get(reverse("session-list"))

        sessions = response.data["sessions"]
        assert len(sessions) == 1
        assert sessions[0]["is_current"] is True

    def test_non_current_session_marked_false(self, auth_client, user):
        """Sessions on other devices have is_current=False."""
        make_session(user, raw_token="other_device_token", device_id=str(uuid.uuid4()))

        response = auth_client.get(reverse("session-list"))
        # auth_client has device_id="test-device-abc", row has a different device_id
        assert response.data["sessions"][0]["is_current"] is False

    def test_token_hash_never_exposed(self, auth_client, user):
        """token_hash must NEVER appear in the response."""
        make_session(user, raw_token="secret_raw_token_789")

        response = auth_client.get(reverse("session-list"))

        import json
        body = json.dumps(response.data)
        assert "token_hash" not in body
        assert make_token_hash("secret_raw_token_789") not in body

    def test_ordered_by_last_used_at_desc(self, auth_client, user):
        """Most recently used session comes first."""
        old_id = str(uuid.uuid4())
        new_id = str(uuid.uuid4())

        old = make_session(user, raw_token="old_token", device_id=old_id)
        old.last_used_at = timezone.now() - timedelta(days=5)
        old.save()

        new = make_session(user, raw_token="new_token", device_id=new_id)
        new.last_used_at = timezone.now() - timedelta(minutes=5)
        new.save()

        response = auth_client.get(reverse("session-list"))
        sessions = response.data["sessions"]

        assert str(sessions[0]["session_id"]) == str(new.id)
        assert str(sessions[1]["session_id"]) == str(old.id)

    def test_requires_authentication(self, anon_client):
        """Unauthenticated request is rejected by the configured test auth backend."""
        response = anon_client.get(reverse("session-list"))
        assert response.status_code == 401

    def test_does_not_return_other_users_sessions(self, auth_client, other_user):
        """User A cannot see User B's sessions."""
        make_session(other_user, raw_token="other_session_token")

        response = auth_client.get(reverse("session-list"))
        assert response.data["sessions"] == []

    def test_empty_list_when_no_active_sessions(self, auth_client):
        """No sessions → empty list, not 404."""
        response = auth_client.get(reverse("session-list"))
        assert response.status_code == 200
        assert response.data["sessions"] == []


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/auth/sessions/<session_id>/
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionRevoke:

    def test_revoke_own_session(self, auth_client, user):
        """Owner can revoke their own session by UUID."""
        session = make_session(user, raw_token="revoke_me_token")

        response = auth_client.delete(
            reverse("session-revoke", kwargs={"session_id": session.id})
        )

        assert response.status_code == 200
        assert response.data["message"] == "Session revoked."

        session.refresh_from_db()
        assert session.revoked is True

    def test_revoke_nonexistent_returns_404(self, auth_client):
        """Random UUID → 404."""
        response = auth_client.delete(
            reverse("session-revoke", kwargs={"session_id": uuid.uuid4()})
        )
        assert response.status_code == 404

    def test_cannot_revoke_other_users_session(self, auth_client, other_user):
        """
        User A tries to revoke User B's session.
        Returns 404 — not 403 — to avoid confirming the session exists.
        """
        their_session = make_session(other_user, raw_token="their_secret_token")

        response = auth_client.delete(
            reverse("session-revoke", kwargs={"session_id": their_session.id})
        )

        assert response.status_code == 404  # Not 403

        their_session.refresh_from_db()
        assert their_session.revoked is False  # untouched

    def test_revoke_already_revoked_returns_404(self, auth_client, user):
        """Already-revoked session → 404, not 200."""
        session = make_session(user, raw_token="double_revoke_token", revoked=True)

        response = auth_client.delete(
            reverse("session-revoke", kwargs={"session_id": session.id})
        )
        assert response.status_code == 404

    def test_revoke_expired_session_returns_404(self, auth_client, user):
        """Expired session → 404."""
        session = make_session(user, raw_token="expired_token", expired=True)

        response = auth_client.delete(
            reverse("session-revoke", kwargs={"session_id": session.id})
        )
        assert response.status_code == 404

    def test_revoking_current_session_clears_cookie(self, user):
        """
        If the revoked session matches the JWT's device_id,
        the response must clear the refresh_token cookie.
        """
        device_id = str(uuid.uuid4())
        session = make_session(user, raw_token="curr_device_token", device_id=device_id)

        client = APIClient()
        client.force_authenticate(user=user, token={"device_id": device_id})

        response = client.delete(
            reverse("session-revoke", kwargs={"session_id": session.id})
        )

        assert response.status_code == 200
        cookie = response.cookies.get("refresh_token")
        assert cookie is not None
        assert cookie.value == "" or cookie["max-age"] == 0

    def test_revoking_other_device_does_not_clear_cookie(self, auth_client, user):
        """
        Revoking a different device's session must NOT clear the current device's cookie.
        """
        other_device_id = str(uuid.uuid4())  # different from auth_client's "test-device-abc"
        session = make_session(user, raw_token="other_device_tok", device_id=other_device_id)

        response = auth_client.delete(
            reverse("session-revoke", kwargs={"session_id": session.id})
        )

        assert response.status_code == 200
        # Cookie should not be set / cleared in this response
        cookie = response.cookies.get("refresh_token")
        if cookie:
            # If set, it must NOT be an expiry (that would sign out current device)
            assert cookie["max-age"] != 0

    def test_requires_authentication(self, anon_client, user):
        """Unauthenticated request is rejected by the configured test auth backend."""
        session = make_session(user, raw_token="unauth_test_token")
        response = anon_client.delete(
            reverse("session-revoke", kwargs={"session_id": session.id})
        )
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /api/auth/sessions/all/
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionRevokeAll:

    def test_revokes_all_active_sessions(self, auth_client, user):
        """All active sessions for current user are revoked."""
        for i in range(3):
            make_session(user, raw_token=f"bulk_token_{i}")

        response = auth_client.delete(reverse("session-revoke-all"))

        assert response.status_code == 200
        assert response.data["revoked_count"] == 3
        assert response.data["message"] == "All sessions revoked."

        assert RefreshToken.objects.filter(user=user, revoked=False).count() == 0

    def test_does_not_count_already_revoked(self, auth_client, user):
        """Already-revoked sessions are not included in revoked_count."""
        make_session(user, raw_token="active_tok")
        make_session(user, raw_token="already_revoked_tok", revoked=True)

        response = auth_client.delete(reverse("session-revoke-all"))

        assert response.data["revoked_count"] == 1

    def test_does_not_affect_other_users(self, auth_client, other_user):
        """Revoke-all never touches other users' sessions."""
        their_session = make_session(other_user, raw_token="their_tok")

        auth_client.delete(reverse("session-revoke-all"))

        their_session.refresh_from_db()
        assert their_session.revoked is False

    def test_clears_refresh_cookie(self, auth_client, user):
        """Response must expire the refresh_token cookie."""
        make_session(user, raw_token="cookie_test_tok")

        response = auth_client.delete(reverse("session-revoke-all"))

        cookie = response.cookies.get("refresh_token")
        assert cookie is not None
        assert cookie.value == "" or cookie["max-age"] == 0

    def test_zero_sessions_returns_zero_count(self, auth_client):
        """No active sessions → revoked_count=0, no error."""
        response = auth_client.delete(reverse("session-revoke-all"))
        assert response.status_code == 200
        assert response.data["revoked_count"] == 0

    def test_requires_authentication(self, anon_client):
        """Unauthenticated request is rejected by the configured test auth backend."""
        response = anon_client.delete(reverse("session-revoke-all"))
        assert response.status_code == 401
