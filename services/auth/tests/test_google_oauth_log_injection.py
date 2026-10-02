"""The Google OAuth denial log line must stay a single log record.

`error` is a raw query parameter on an unauthenticated endpoint, and auth's
`verbose` formatter (`{levelname} {asctime} {module} {message}`) writes the
message verbatim. A CR/LF in the value would therefore let a caller append
an arbitrary, well-formed-looking record to the audit log.

This drives the real view. An earlier version of this file re-implemented
the escaping inside the test body, which passed even after the escaping was
removed from the view - a vacuous test, caught by fault injection.
"""

import io
import logging
import re

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

# Turns one record into two. The second line is shaped exactly like a real
# record - level, timestamp, module - so a log parser cannot tell it apart.
FORGERY = "access_denied\r\nINFO 2026-01-01 00:00:00 authentication.views forged_entry"

RECORD = re.compile(r"^(?:TRACE|DEBUG|INFO|WARNING|ERROR|CRITICAL) \d{4}-\d{2}-\d{2} ")

LOGGER_NAME = "authentication.oauth.google.views"


def record_lines(output: str) -> list[str]:
    """Lines a log parser would read as separate records."""
    return [line for line in output.splitlines() if RECORD.match(line)]


@pytest.fixture
def captured_view_logger():
    """Attach a handler to the view's own logger and yield the buffer."""
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
def client():
    return APIClient()


@pytest.fixture
def callback_url():
    return reverse("google-oauth-callback")


@pytest.mark.django_db
class TestDenialLogCannotBeForged:
    def test_crlf_in_the_error_param_forges_no_extra_record(
        self, client, callback_url, captured_view_logger
    ):
        response = client.get(callback_url, {"error": FORGERY})

        assert response.status_code == 400
        records = record_lines(captured_view_logger.getvalue())
        assert len(records) == 1, (
            "the payload produced more than one log record:\n"
            f"{captured_view_logger.getvalue()}"
        )

    def test_the_parameter_is_still_recorded_in_escaped_form(
        self, client, callback_url, captured_view_logger
    ):
        """Escaped, not discarded: the value has to stay diagnosable."""
        client.get(callback_url, {"error": FORGERY})

        output = captured_view_logger.getvalue()
        assert "google_oauth_user_denied" in output
        assert "\\r\\n" in output
        assert "forged_entry" in output  # not stripped away

    def test_a_legitimate_denial_is_unchanged(
        self, client, callback_url, captured_view_logger
    ):
        response = client.get(callback_url, {"error": "access_denied"})

        assert response.status_code == 400
        assert "error=access_denied" in captured_view_logger.getvalue()

    def test_the_client_response_does_not_echo_the_parameter(
        self, client, callback_url
    ):
        """The response is separate from the log, and must stay generic."""
        response = client.get(callback_url, {"error": FORGERY})

        body = response.content.decode()
        assert "access_denied" not in body
        assert response.json()["error_code"] == "oauth_denied"
