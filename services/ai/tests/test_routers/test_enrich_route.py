"""The route is where the summary's reason stops being lost in translation.

The service now produces `ai_summary_error`, and that is worth nothing unless it
survives the trip through the response model. Two things in this router were
actively destroying it:

`EnrichResponse.ai_executive_summary` was `str = ""` while the service had been
returning `str | None` since before this work started. The type system was
actively inviting the flattening, and `result.get("ai_executive_summary", "")`
performed it: a summary that failed and a summary that was never requested both
serialised to `""`. There was no field for the error at all, so even had the
service kept it, the route would have dropped it on the floor.

The route also had no rate limit and no backpressure slot, while its sibling
`/chat` had both. Enrichment is not a cheap endpoint -- it fans out across five
finding categories and then runs the summary model loop, all on the shared
master key -- so an unbounded number of concurrent calls could hold every worker
in the service.

These call the handler directly rather than going through `TestClient`, matching
`test_chat.py`. The point is the handler's own logic: what it puts in the
response, and what it releases.
"""

from collections.abc import Callable
from typing import cast

import asyncio
import pytest
from fastapi import HTTPException

from app.api.dependencies.auth import JWTPayload
from app.api.routers import analysis as router_module
from app.api.routers.analysis import (
    ENRICH_REQUEST_TIMEOUT_SECONDS,
    AiSummaryError,
    EnrichFindingItem,
    EnrichRequest,
    EnrichResponse,
    enrich_analysis,
)

pytestmark = pytest.mark.unit

# Built as the models rather than as dicts, so a field rename in either schema is
# a failure here rather than a `**kwargs` mismatch that mypy flags and pytest does
# not. These are the *service's* response shape, which is deliberately looser than
# the models -- the handler is what narrows it.
_FINDING: dict[str, object] = {
    "title": "SQL injection in user lookup",
    "category": "security",
    "severity": "HIGH",
    "file_path": "app/users.py",
    "line_start": 42,
}

_ERROR: dict[str, object] = {
    "code": "rate_limited",
    "message": "AI service is busy. Please try again shortly.",
    "suggested_action": "wait",
    "retry_after": 30,
}


class _Recorder:
    """Stands in for the LLM slot, so acquisition and release are observable."""

    def __init__(self) -> None:
        self.acquired = 0
        self.released = 0

    async def acquire(self) -> None:
        self.acquired += 1

    async def release(self) -> None:
        self.released += 1

    @property
    def outstanding(self) -> int:
        return self.acquired - self.released


@pytest.fixture
def slot(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    """Replace the real backpressure globals, which are uninitialised in tests.

    `acquire_llm_slot` returns early when the semaphore is None and
    `release_llm_slot` only decrements a module counter, so without this both are
    unobservable and the leak this file is about would be invisible to it.
    """
    recorder = _Recorder()
    monkeypatch.setattr(router_module, "acquire_llm_slot", recorder.acquire)
    monkeypatch.setattr(router_module, "release_llm_slot", recorder.release)
    return recorder


# The three ways a stubbed `enrich` can behave, which is every way this file
# needs. Named constructors rather than injecting a callable: the injectable
# version needed `Callable[..., Awaitable[...]]`, whose ellipsis is implicitly
# `Any` under this project's mypy config, so every test that used it paid an
# `explicit-any` for a distinction that is really an enumeration.
_STALL = object()


def _returning(result: dict[str, object]) -> _Stub:
    return _Stub(result=result)


def _raising(error: Exception) -> _Stub:
    return _Stub(error=error)


def _stalling() -> _Stub:
    return _Stub(stall=True)


class _Stub:
    """Enough of `EnrichmentService` for the handler.

    `_get_enrichment` is annotated `-> EnrichmentService`, so a test that patched
    it with a `cast("object", ...)` made mypy complain about the test rather than
    about the thing under test. Passing the stub directly keeps the patch honest.

    `stall` sleeps past any deadline a test sets rather than raising, so the
    timeout under test is the one that has to fire. The unreachable `raise` after
    it exists so a test whose bound is not actually enforcing anything fails
    naming the cause, instead of passing because the backstop never mattered.
    """

    def __init__(
        self,
        *,
        result: dict[str, object] | None = None,
        error: Exception | None = None,
        stall: bool = False,
    ) -> None:
        self._result = result
        self._error = error
        self._stall = stall

    async def enrich(self, **kwargs: object) -> dict[str, object]:
        if self._stall:
            await asyncio.sleep(30)
            raise AssertionError("the deadline did not fire")
        if self._error is not None:
            raise self._error
        assert self._result is not None, "stub built with no result and no error"
        return self._result


_InstallService = Callable[[dict[str, object]], None]
"""The `service` fixture: takes the response the stubbed service should return."""


@pytest.fixture
def service(monkeypatch: pytest.MonkeyPatch) -> _InstallService:
    """Replace the service with a stub whose `enrich` a test controls."""

    def install(result: dict[str, object]) -> None:
        _install_stub(monkeypatch, _returning(result))

    return install


def _install_stub(monkeypatch: pytest.MonkeyPatch, stub: _Stub) -> None:
    monkeypatch.setattr(router_module, "_get_enrichment", lambda: stub)


_USER = JWTPayload(sub="user-1", email="user@example.com")

# Built as the model rather than unpacked from `_FINDING`: `**` into typed keyword
# parameters cannot be checked against `dict[str, object]`, and a field rename in
# the schema should fail here rather than be absorbed by a cast.
_REQUEST_FINDING = EnrichFindingItem(
    title="SQL injection in user lookup",
    category="security",
    severity="HIGH",
    file_path="app/users.py",
    line_start=42,
)


async def _call() -> EnrichResponse:
    """Invoke the handler with one finding.

    Parameterless on purpose: every test in this file sends the same request, and
    an `**overrides` escape hatch would only have been used once per test to pass
    that same request back in.
    """
    request = EnrichRequest(findings=[_REQUEST_FINDING])
    return await enrich_analysis(request=request, _user=_USER, _=None)


def _detail(exc: HTTPException) -> dict[str, object]:
    """`HTTPException.detail` is `Any`, so indexing it is unchecked. Narrow it here."""
    return cast("dict[str, object]", exc.detail)


# ======================================================================
# The error survives
# ======================================================================


class TestTheErrorReachesTheClient:
    async def test_a_summary_failure_is_a_200_with_a_reason(
        self, service: _InstallService, slot: _Recorder
    ) -> None:
        # The contract this whole change exists to establish. The findings are
        # worth keeping, so the response is a success -- and it says why the one
        # missing field is missing.
        service(
            {"findings": [], "ai_executive_summary": None, "ai_summary_error": _ERROR}
        )

        response = await _call()

        assert response.ai_executive_summary is None
        assert response.ai_summary_error is not None
        assert response.ai_summary_error.code == "rate_limited"
        assert response.ai_summary_error.suggested_action == "wait"
        assert response.ai_summary_error.retry_after == 30

    async def test_a_successful_enrichment_carries_no_error(
        self, service: _InstallService, slot: _Recorder
    ) -> None:
        service(
            {
                "findings": [],
                "ai_executive_summary": "## Assessment\n\nNot ready.",
                "ai_summary_error": None,
            }
        )

        response = await _call()

        assert response.ai_executive_summary == "## Assessment\n\nNot ready."
        assert response.ai_summary_error is None

    async def test_the_findings_are_present_alongside_the_error(
        self, service: _InstallService, slot: _Recorder
    ) -> None:
        # Why this is a degraded 200 and not a 4xx or 5xx at all. A client that
        # sees a non-2xx has no choice but to discard the response, and the
        # response is the report.
        service(
            {
                "findings": [
                    {**_FINDING, "ai_explanation": "Because.", "is_ai_enriched": True}
                ],
                "ai_executive_summary": None,
                "ai_summary_error": _ERROR,
            }
        )

        response = await _call()

        assert len(response.findings) == 1
        assert response.findings[0].ai_explanation == "Because."
        assert response.ai_summary_error is not None

    async def test_a_missing_summary_is_null_not_an_empty_string(
        self, service: _InstallService, slot: _Recorder
    ) -> None:
        # `""` is the value that made this bug invisible: it meant both "failed"
        # and "never asked for". `EnrichResponse` no longer accepts it -- see
        # `test_a_blank_summary_is_rejected_rather_than_serialised` -- so a caller
        # cannot reintroduce the ambiguity at this layer.
        service(
            {"findings": [], "ai_executive_summary": None, "ai_summary_error": None}
        )

        response = await _call()

        assert response.ai_executive_summary is None
        with pytest.raises(ValueError):
            EnrichResponse(findings=[], ai_executive_summary="")

    async def test_a_service_that_omits_the_summary_key_does_not_500(
        self, service: _InstallService, slot: _Recorder
    ) -> None:
        # `.get` rather than `[]`. The service is a collaborator across a process
        # boundary, and a missing key should not become a 500 in the middle of an
        # otherwise successful enrichment.
        service({"findings": []})

        response = await _call()

        assert response.ai_executive_summary is None
        assert response.findings == []


# ======================================================================
# The schema is the leak boundary
# ======================================================================


class TestTheSchemaRefusesToBeMorePermissive:
    def test_there_is_no_field_for_raw_provider_output(self) -> None:
        # The temptation, when adding an error object, is to include the provider's
        # own words so support can see them. `technical_message` is the provider's
        # verbatim response body, and for an auth failure it contains the rejected
        # key. The schema has no such field, so there is nothing to forget to
        # remove.
        fields = set(AiSummaryError.model_fields)

        assert fields == {"code", "message", "suggested_action", "retry_after"}
        for forbidden in (
            "provider",
            "model",
            "technical_message",
            "detail",
            "error",
            "raw",
            "traceback",
        ):
            assert forbidden not in fields

    def test_an_unknown_extra_field_is_rejected_rather_than_silently_kept(self) -> None:
        # `extra="ignore"` would let a future change to the service silently start
        # forwarding `provider` and `model` to a browser, with this test still
        # passing -- because the widening happens at the moment nobody is looking
        # at this file. Under `forbid` the same change is a construction error.
        #
        # mypy flags the extra keywords here, correctly: statically they cannot
        # be passed. That is the point of the test, so the warnings are expected.
        with pytest.raises(ValueError):
            AiSummaryError(  # type: ignore[call-arg]
                code="auth_failed",
                message="Authentication failed.",
                suggested_action="check_key",
                provider="openrouter",
                model="some/model",
            )

    def test_retry_after_may_be_absent_but_not_meaningless(self) -> None:
        # Built field by field rather than `**`-unpacked, so the absence of
        # `retry_after` is stated by the absence of a line rather than by a filter
        # over a dict -- which is also what makes the `exclude_unset` assertion
        # below meaningful rather than an artefact of the filtering.
        without_hint = AiSummaryError(
            code="provider_unavailable",
            message="AI service is temporarily unavailable.",
            suggested_action="retry",
        )

        assert "retry_after" not in without_hint.model_dump(exclude_unset=True)
        assert without_hint.retry_after is None
        assert (
            AiSummaryError(
                code="rate_limited",
                message="busy",
                suggested_action="wait",
                retry_after=0,
            ).retry_after
            == 0
        )

    def test_a_blank_summary_is_rejected_rather_than_serialised(self) -> None:
        # The value this whole change is about. `str | None` permits `""`, and
        # `""` is precisely what cannot be told apart from a generation failure --
        # so the guarantee is a validator, not a type. The service already refuses
        # to produce one; this means the *next* path that returns `""` is an error
        # rather than a card that silently renders nothing.
        for blank in ("", "   ", "\n\n\t"):
            with pytest.raises(ValueError, match="non-blank"):
                EnrichResponse(findings=[], ai_executive_summary=blank)

        assert EnrichResponse(findings=[], ai_executive_summary=None)
        assert EnrichResponse(findings=[], ai_executive_summary="## Assessment")


# ======================================================================
# Bounds
# ======================================================================


class TestTheRequestIsBounded:
    async def test_a_stalled_findings_enrichment_is_a_504(
        self, service: _InstallService, slot: _Recorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A real 504, unlike the summary's timeout. At this point the findings
        # enrichment has not returned, so there is nothing to salvage and a
        # degraded 200 would claim work that did not happen.
        monkeypatch.setattr(router_module, "ENRICH_REQUEST_TIMEOUT_SECONDS", 0.05)
        _install_stub(monkeypatch, _stalling())

        with pytest.raises(HTTPException) as raised:
            await _call()

        assert raised.value.status_code == 504
        detail = _detail(raised.value)
        assert detail["error"] == "enrichment_timeout"
        assert detail["retry_after"] == 30

    def test_the_backstop_leaves_room_for_the_summaries_own_deadline(self) -> None:
        # The service bounds the summary at 75s. If this backstop were tighter than
        # that, it would always win and the summary's specific, actionable
        # `timeout` error would be unreachable -- replaced by a generic 504 that
        # names neither the provider nor the fact that retrying is worth trying.
        from app.application.analysis.enrichment import SUMMARY_TIMEOUT_SECONDS

        assert ENRICH_REQUEST_TIMEOUT_SECONDS > SUMMARY_TIMEOUT_SECONDS

    def test_the_backstop_is_below_the_callers_own_timeout(self) -> None:
        # Same reasoning one level up: a bound that fires after the caller has
        # given up is not a bound. The analysis service allows 120s.
        assert ENRICH_REQUEST_TIMEOUT_SECONDS < 120


class TestTheSlotIsNotLeaked:
    async def test_a_successful_call_releases_its_slot(
        self, service: _InstallService, slot: _Recorder
    ) -> None:
        service(
            {"findings": [], "ai_executive_summary": None, "ai_summary_error": _ERROR}
        )

        await _call()

        assert slot.acquired == 1
        assert slot.outstanding == 0

    async def test_a_timed_out_call_releases_its_slot(
        self, service: _InstallService, slot: _Recorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The one that actually matters. `MAX_CONCURRENT_LLM_CHAINS` is 10; a
        # handler that acquires and does not release on the error path turns one
        # slow provider into a service that is out of slots permanently, and the
        # symptom is a 503 on every endpoint that uses one -- including `/chat`,
        # which shares the semaphore.
        monkeypatch.setattr(router_module, "ENRICH_REQUEST_TIMEOUT_SECONDS", 0.05)
        _install_stub(monkeypatch, _stalling())

        with pytest.raises(HTTPException):
            await _call()

        assert slot.acquired == 1
        assert slot.outstanding == 0

    async def test_an_unexpected_service_error_releases_its_slot(
        self, slot: _Recorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Not just the timeout path. Anything raised out of `enrich()` -- a
        # database error, a bug in finding construction -- takes the same route
        # through the `finally`, and a `try/except/finally` where the `finally`
        # only covers the happy path is a leak that looks correct in review.
        _install_stub(monkeypatch, _raising(RuntimeError("database is on fire")))

        with pytest.raises(RuntimeError, match="on fire"):
            await _call()

        assert slot.acquired == 1
        assert slot.outstanding == 0
