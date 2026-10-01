"""Tests for the error boundaries that stop internal exception text reaching clients.

`log_and_raise` exists because `raise SomeError(str(exc))` returns whatever
the raising code put in the exception, and for errors that wrap a third-party
call that text includes the upstream library's message and up to 200
characters of the upstream response body.

These tests attach their own handler to the `core.exceptions` logger instead
of using `caplog`. `caplog` captures via the root logger, and the wider suite
mutates root logging state, so the first version of these tests passed alone
and failed with `IndexError` on `caplog.records[-1]` under a full run. Owning
the handler makes the assertions depend only on `log_and_raise`.
"""

import logging
import pytest
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from core.exceptions import log_and_raise

pytestmark = pytest.mark.unit

LOGGER_NAME = "core.exceptions"


class _CollectingHandler(logging.Handler):
    """Collects the records emitted while the test runs."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    @property
    def last(self) -> logging.LogRecord:
        assert self.records, (
            f"{LOGGER_NAME} emitted no records; the capture handler is not "
            "wired to the logger the code under test uses"
        )
        return self.records[-1]


def _capture_log_records():
    """Yield a collecting handler attached to `core.exceptions`.

    Two pieces of global state have to be undone for a record to arrive at
    all, and neither is anything to do with `log_and_raise`:

    * ``core/settings/test.py`` sets ``disable_existing_loggers: True``, so
      when Django runs ``dictConfig`` every logger that already existed is
      left with ``disabled = True`` permanently - ``Logger.handle`` returns
      before any handler runs. Whether ``core.exceptions`` is caught depends
      on import order, which is why this file passed alone and failed under a
      full run.
    * A module-level ``logging.disable()`` throttles all loggers regardless
      of their level.

    Both are saved and restored, so the fixture leaves global state as found.
    """
    logger = logging.getLogger(LOGGER_NAME)
    handler = _CollectingHandler()

    previous_level = logger.level
    previous_disabled = logger.disabled
    previous_global = logging.root.manager.disable

    logger.addHandler(handler)
    logger.disabled = False
    logger.setLevel(logging.DEBUG)
    logging.disable(logging.NOTSET)
    try:
        yield handler
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.disabled = previous_disabled
        logging.disable(previous_global)


@pytest.fixture
def captured() -> _CollectingHandler:
    """Capture records emitted by `core.exceptions` during one test."""
    yield from _capture_log_records()


@pytest.fixture
def captured_from_disabled_logger() -> _CollectingHandler:
    """As `captured`, but starting from the state `dictConfig` leaves behind.

    The sabotage has to happen *before* the capture fixture sets up, since
    re-enabling the logger is the fixture's job. Sabotaging it inside the test
    body instead would prove nothing.
    """
    logging.getLogger(LOGGER_NAME).disabled = True
    yield from _capture_log_records()


@pytest.fixture
def captured_under_global_throttle() -> _CollectingHandler:
    """As `captured`, but with `logging.disable()` already in effect."""
    logging.disable(logging.CRITICAL)
    yield from _capture_log_records()


def _raise(exc, detail, cls=ValidationError, message="test.raise", **kwargs):
    with pytest.raises(cls):
        log_and_raise(exc, detail, cls, log_message=message, **kwargs)


class TestLogAndRaiseRaisesTheRightThing:
    def test_raises_the_requested_exception_class(self):
        _raise(ValueError("boom"), "Something went wrong.", ValidationError)

    def test_raises_not_found(self):
        _raise(ValueError("boom"), "Gone.", NotFound)

    def test_raises_permission_denied(self):
        _raise(ValueError("boom"), "Nope.", PermissionDenied)

    @pytest.mark.parametrize(
        ("exc_cls", "expected_status"),
        [(ValidationError, 400), (PermissionDenied, 403), (NotFound, 404)],
    )
    def test_preserves_the_http_semantics_of_each_class(self, exc_cls, expected_status):
        with pytest.raises(exc_cls) as caught:
            log_and_raise(ValueError("x"), "nope", exc_cls, log_message="test.status")
        assert caught.value.status_code == expected_status

    def test_chains_the_original_exception(self):
        """`from exc` semantics: the client-facing error keeps the cause."""
        original = ValueError("root cause")
        with pytest.raises(ValidationError) as caught:
            log_and_raise(original, "nope", ValidationError, log_message="test.chain")
        assert caught.value.__cause__ is original

    def test_does_not_mutate_the_original_exception(self):
        original = ValueError("root cause")
        _raise(original, "nope")
        assert str(original) == "root cause"


class TestInternalDetailDoesNotReachTheClient:
    """The defect these guard: `str(exc)` was the response body."""

    # Shaped like the real GitHub App failure: requests' own text (host, port)
    # plus the first slice of the upstream response body.
    INTERNAL = (
        "Failed to request installation token: "
        "HTTPSConnectionPool(host='github.internal.corp', port=443): "
        "token=ghs_secretvalue body={'internal_note':'db-primary-3'}"
    )
    FORBIDDEN = (
        "github.internal.corp",
        "ghs_secretvalue",
        "db-primary-3",
        "HTTPSConnectionPool",
    )

    def test_response_carries_the_public_message_only(self):
        with pytest.raises(ValidationError) as caught:
            log_and_raise(
                ValueError(self.INTERNAL),
                "Could not reach GitHub. Please try again later.",
                ValidationError,
                log_message="test.no_leak",
            )

        rendered = str(caught.value)
        assert "Could not reach GitHub" in rendered
        for secret in self.FORBIDDEN:
            assert secret not in rendered, f"{secret!r} leaked to the client"

    def test_internal_detail_is_still_available_to_operators(self, captured):
        """Moving the detail out of the response must not lose it entirely."""
        with pytest.raises(ValidationError):
            log_and_raise(
                ConnectionError(self.INTERNAL),
                "Could not reach GitHub. Please try again later.",
                ValidationError,
                log_message="test.detail_preserved",
            )

        record = captured.last
        assert record.getMessage() == "test.detail_preserved"
        for secret in self.FORBIDDEN:
            assert secret in record.error, f"{secret!r} missing from the log record"

    def test_diagnostic_fields_are_populated(self, captured):
        _raise(
            ConnectionError("connection refused to redis-primary:6379"),
            "Service temporarily unavailable.",
            message="test.fields",
        )

        record = captured.last
        assert record.error == "connection refused to redis-primary:6379"
        assert record.error_type == "ConnectionError"

    def test_caller_context_is_preserved(self, captured):
        _raise(
            ValueError("x"),
            "nope",
            message="test.extra",
            log_extra={"actor_id": "user-123"},
        )

        assert captured.last.actor_id == "user-123"

    def test_log_extra_is_optional(self, captured):
        _raise(ValueError("x"), "nope", NotFound, message="test.no_extra")
        assert captured.last.getMessage() == "test.no_extra"

    def test_a_message_is_always_logged_even_with_no_context(self, captured):
        """If logging were skipped the client would lose all diagnostics."""
        _raise(ValueError("x"), "nope", message="test.always")
        assert len(captured.records) == 1


class TestCaptureSurvivesGlobalLoggingState:
    """Guards the capture fixture against pre-existing global state.

    `core/settings/test.py` sets `disable_existing_loggers: True`, so a logger
    that already exists when Django calls `dictConfig` is left permanently
    disabled and emits nothing. Whether `core.exceptions` is caught by that
    depends on import order, which is what made this file pass alone and fail
    with "emitted no records" under a full run. These pin the fixture's
    ability to recover, so that failure cannot return as a mystery.
    """

    def test_capture_works_when_the_logger_was_left_disabled(
        self, captured_from_disabled_logger
    ):
        _raise(ValueError("x"), "nope", message="test.disabled_logger")
        assert captured_from_disabled_logger.last.getMessage() == (
            "test.disabled_logger"
        )

    def test_capture_works_when_logging_is_globally_throttled(
        self, captured_under_global_throttle
    ):
        _raise(ValueError("x"), "nope", message="test.global_disable")
        assert captured_under_global_throttle.last.getMessage() == (
            "test.global_disable"
        )


class TestTracebackCapture:
    def test_records_a_traceback_when_one_exists(self, captured):
        try:
            raise ConnectionError("upstream died")
        except ConnectionError as exc:
            with pytest.raises(ValidationError):
                log_and_raise(
                    exc, "Upstream failed.", ValidationError, log_message="test.tb"
                )

        assert "raise ConnectionError" in captured.last.traceback

    def test_traceback_is_none_when_the_exception_was_never_raised(self, captured):
        """An unraised exception has no __traceback__; logging must not crash."""
        _raise(ValueError("never raised"), "Something failed.", message="test.no_tb")

        assert captured.last.traceback is None

    def test_frame_is_logged_when_the_call_sites_run(self, captured):
        """`log_and_raise` is called from a real `except` block in the views.

        A traceback captured there must name the view frame, which is what
        makes the log record useful for locating the failure.
        """
        try:
            raise ValueError("from the view")
        except ValueError as exc:
            try:
                _raise(exc, "Client message.", message="test.frames")
            except Exception:  # noqa: BLE001 - only to capture and re-raise
                raise

        trace = captured.last.traceback
        assert trace, "expected a traceback from a real except block"
        assert "raise ValueError" in trace
