"""Why the extra={...} log-injection sites needed no behavioural change.

Auth's `verbose` formatter is `{levelname} {asctime} {module} {message}`.
Only `message` is rendered, so a value passed only through `extra={...}`
never reaches the log line at all and cannot forge a record -- 10 auth and
25 core alerts. Values interpolated into the format string *do* reach the
line, which is what the view tests in `test_google_oauth_log_injection.py`
and `test_views_log_injection.py` cover.

Those extra-only sites have since been wrapped in `log_safe()` anyway, as
defense in depth: correctness here currently rests on a formatter nobody
reads when adding a field. Sanitising at the sink removes that dependency,
and it is what lets the alerts close as fixed rather than as dismissed.

The behaviour asserted below is unchanged by that wrapping -- a sanitised
value still never reaches the rendered line. These tests now pin the
*precondition* the wrapping defends: if someone adds `%(error)s` to the
verbose format string, this is what makes it visible that those call sites
would have been forgeable but for the sanitiser.
"""

import io
import logging

import pytest

# A CR/LF payload whose second line is shaped exactly like a real record -
# level, timestamp, module - which is what a log parser cannot distinguish
# from a genuine entry.
FORGERY = "10.0.0.1\r\nINFO 2026-01-01 00:00:00 authentication.views forged_entry"

# The exact formatter from auth/settings/base.py:443.
AUTH_VERBOSE = {"fmt": "{levelname} {asctime} {module} {message}", "style": "{"}


@pytest.fixture
def rendered():
    """Capture what a single logger call actually writes."""

    def _capture(call):
        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(
            logging.Formatter(datefmt="%Y-%m-%d %H:%M:%S", **AUTH_VERBOSE)
        )
        logger = logging.getLogger("test.loginj.auth")
        logger.handlers = [handler]
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        try:
            call(logger)
        finally:
            logger.handlers = []
        return buf.getvalue().rstrip("\n")

    return _capture


class TestExtraOnlySitesAreNotForgeable:
    def test_extra_fields_never_reach_the_rendered_line(self, rendered):
        def _call(logger):
            logger.error("github.token.decryption_failed", extra={"error": FORGERY})

        out = rendered(_call)
        assert len(out.splitlines()) == 1
        assert "forged" not in out

    def test_str_of_an_exception_in_extra_is_also_inert(self, rendered):
        """The shape used by the oauth token endpoints."""
        try:
            raise ValueError(FORGERY)
        except ValueError as exc:
            # Bound before use: Python unbinds `exc` at the end of the
            # handler, so a closure over it would be fragile.
            detail = str(exc)

        out = rendered(
            lambda logger: logger.error(
                "github.token.decryption_failed",
                extra={"user_id": "u1", "error": detail},
            )
        )

        assert len(out.splitlines()) == 1
        assert "forged" not in out

    def test_the_verbose_format_renders_only_message(self):
        formatter = logging.Formatter(datefmt="%Y-%m-%d %H:%M:%S", **AUTH_VERBOSE)
        assert "{message}" in formatter._style._fmt
        for field in ("error", "ip", "user_id", "workspace_id"):
            assert field not in formatter._style._fmt


class TestInterpolatedValuesAreForgeable:
    """The contrast that makes the two view tests necessary."""

    def test_the_same_payload_in_the_format_string_is_forgeable(self, rendered):
        out = rendered(
            lambda logger: logger.info(
                "google_oauth_user_denied: ip=%s error=%s", "10.0.0.1", FORGERY
            )
        )

        assert len(out.splitlines()) == 2
        assert out.splitlines()[1].startswith("INFO ")

    def test_escaping_both_characters_defuses_it(self, rendered):
        out = rendered(
            lambda logger: logger.info(
                "google_oauth_user_denied: ip=%s error=%s",
                "10.0.0.1",
                FORGERY.replace("\r", "\\r").replace("\n", "\\n"),
            )
        )

        assert len(out.splitlines()) == 1
        assert "\\r\\n" in out
