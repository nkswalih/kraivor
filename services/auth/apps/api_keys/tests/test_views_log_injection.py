"""The API-key revoke failure log line must stay a single log record.

`key_id` is matched by the `<str:key_id>` URL converter, which accepts CR
and LF, and auth's `verbose` formatter writes the message verbatim. A CR/LF
in the path would let a caller append an arbitrary, well-formed-looking
record to the audit log.

This drives the real view. An earlier version re-implemented the escaping
inside the test body, which passed even after the escaping was removed from
the view - a vacuous test, caught by fault injection.
"""

import io
import logging
import re
import uuid
from unittest.mock import patch

import pytest
from api_keys.models import APIKey
from api_keys.services.key_service import create_api_key
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

# Turns one record into two. The second line is shaped exactly like a real
# record - level, timestamp, module - so a log parser cannot tell it apart.
FORGERY = "abc\r\nINFO 2026-01-01 00:00:00 authentication.views forged_entry"

RECORD = re.compile(r"^(?:TRACE|DEBUG|INFO|WARNING|ERROR|CRITICAL) \d{4}-\d{2}-\d{2} ")

LOGGER_NAME = "api_keys.views"


def record_lines(output: str) -> list[str]:
    """Lines a log parser would read as separate records."""
    return [line for line in output.splitlines() if RECORD.match(line)]


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create(
        email="revoke-log@example.com", name="Revoke Log", email_verified=True
    )


@pytest.fixture
def auth_client(user):
    from authentication.tokens import get_token_service

    client = APIClient()
    token_service = get_token_service()
    tokens = token_service.generate_tokens(user, "test-device", "127.0.0.1", "pytest")
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access_token}")
    return client


@pytest.fixture
def captured_view_logger():
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(
        logging.Formatter(
            fmt="{levelname} {asctime} {module} {message}",
            style="{",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger = logging.getLogger(LOGGER_NAME)
    previous_handlers, previous_propagate = logger.handlers, logger.propagate
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    try:
        yield buf
    finally:
        logger.handlers = previous_handlers
        logger.propagate = previous_propagate


@pytest.fixture
def real_key(user):
    result = create_api_key(user=user, name="Key", scopes=["analysis:read"])
    return result.api_key


def revoke_path(key_id: str) -> str:
    """Percent-encode so the CR/LF survives into the URL path."""
    return reverse("api-key-revoke", kwargs={"key_id": key_id}).replace(
        key_id, key_id.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    )


@pytest.mark.django_db
class TestRevokeFailureLogCannotBeForged:
    """`revoke_api_key` is forced to fail so the except branch is reached."""

    def test_crlf_in_the_path_forges_no_extra_record(
        self, auth_client, captured_view_logger
    ):
        with patch("api_keys.views.revoke_api_key", side_effect=RuntimeError("boom")):
            response = auth_client.delete(revoke_path(FORGERY))

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        records = record_lines(captured_view_logger.getvalue())
        assert len(records) == 1, (
            "the payload produced more than one log record:\n"
            f"{captured_view_logger.getvalue()}"
        )

    def test_the_key_id_is_still_recorded_in_escaped_form(
        self, auth_client, captured_view_logger
    ):
        with patch("api_keys.views.revoke_api_key", side_effect=RuntimeError("boom")):
            auth_client.delete(revoke_path(FORGERY))

        output = captured_view_logger.getvalue()
        assert "api_key_revoke_failed" in output
        assert "\\r\\n" in output
        assert "forged_entry" in output  # not stripped away

    def test_the_traceback_is_still_logged(self, auth_client, captured_view_logger):
        """Sanitising the argument must not cost the stack trace."""
        with patch("api_keys.views.revoke_api_key", side_effect=RuntimeError("boom")):
            auth_client.delete(revoke_path(FORGERY))

        assert "Traceback" in captured_view_logger.getvalue()

    def test_the_client_response_is_generic(self, auth_client, captured_view_logger):
        with patch("api_keys.views.revoke_api_key", side_effect=RuntimeError("boom")):
            response = auth_client.delete(revoke_path(FORGERY))

        body = response.content.decode()
        assert "boom" not in body
        assert response.json()["error_code"] == "internal_error"


@pytest.mark.django_db
class TestOrdinaryRevokeStillWorks:
    """Guards the change against breaking the normal path."""

    def test_revoke_returns_200(self, auth_client, real_key):
        response = auth_client.delete(
            reverse("api-key-revoke", kwargs={"key_id": str(real_key.id)})
        )

        assert response.status_code == status.HTTP_200_OK
        assert APIKey.objects.get(id=real_key.id).revoked is True

    def test_unknown_key_returns_404(self, auth_client):
        response = auth_client.delete(
            reverse("api-key-revoke", kwargs={"key_id": str(uuid.uuid4())})
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
