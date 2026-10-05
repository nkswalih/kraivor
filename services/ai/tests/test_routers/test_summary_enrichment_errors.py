"""Why the executive summary stops being a silently-lost field.

Every test here corresponds to a defect that shipped and was fixed.

The summary is the one field of an enrichment response that has no other source.
The findings are computed locally; the summary is the only thing a language model
produced. And it was discarded at the exact point where this service already had
everything it needed to say what went wrong: `ClassifiedError` carries a category,
a user-facing message, a suggested action and a retry hint, and the bare
`except Exception` in `enrich()` threw all four away.

These are written against `EnrichmentService` rather than the HTTP route, because
that is where the error was destroyed. A test at the route would have seen a 200
with `ai_executive_summary: ""` and passed -- which is the shape of the bug.

The test that matters most is `TestDescribeSummaryFailure`. `describe_summary_failure`
is the boundary between an internal exception and a browser, and the property worth
pinning there is that *nothing* reaches a client that should not, which is a
negative assertion about every field on the exception rather than a check that the
four expected fields arrived.
"""

import json
from typing import cast

import asyncio
import pytest
from types import SimpleNamespace

from app.application.analysis import enrichment as module
from app.application.analysis.enrichment import (
    MAX_SUMMARY_MODEL_ATTEMPTS,
    MIN_SUMMARY_CHARS,
    SUMMARY_TIMEOUT_SECONDS,
    EnrichmentService,
    _usable_summary,
    describe_summary_failure,
)
from app.infrastructure.llm.client import LLM_DEFAULT_TIMEOUT
from app.infrastructure.llm.error_classifier import (
    ClassifiedError,
    ErrorCategory,
    SuggestedAction,
    classify_error,
)
from app.infrastructure.llm.router import FREE_MODELS

# ======================================================================
# The stub provider
# ======================================================================
#
# `EnrichmentService` makes two independent kinds of call through the same module
# attribute, and they have to be told apart or a test cannot fail for the reason it
# is about:
#
#   * per-category enrichment, which passes `response_format` and expects JSON;
#   * the executive summary, which passes none and expects prose.
#
# `_generate_executive_summary` builds its own `LLMClient` per model and keeps the
# raw exception, so `responses` is keyed by model id and a model with no entry
# raises rather than silently inheriting the first model's answer -- a test that
# expected an unattempted model to be reached then fails instead of passing for the
# wrong reason.


class _Settings:
    """Reads the key from the stub, so a test can clear it after setup.

    A snapshot taken at fixture time would leave `master_key = ""` in a test that
    sets it afterwards to have no effect, and the missing-key path would go
    untested while looking tested.
    """

    def __init__(self, provider: StubProvider) -> None:
        self._provider = provider

    @property
    def openrouter__master__key(self) -> str:
        return self._provider.master_key


class StubProvider:
    def __init__(self) -> None:
        self.summary_calls: list[str] = []
        self.category_calls: list[str] = []
        self.responses: dict[str, object] = {}
        self.master_key: str = "sk-or-test"
        # Seconds each summary attempt sleeps when set. Used to make a model
        # "slow" without a real 45s wait, so the deadline tests run in
        # milliseconds. Applies to summary calls only -- a hanging category call
        # would hang `asyncio.gather` before the summary is even reached, which is
        # a different failure with a different fix.
        self.summary_delay: float | None = None

    # ── what a test sets ──────────────────────────────────────────────
    def answer_with(self, content: object) -> None:
        """Every summary attempt returns `content` (or raises it if an Exception)."""
        for model in FREE_MODELS:
            self.responses[model] = content

    def fail_with(self, error: Exception) -> None:
        for model in FREE_MODELS:
            self.responses[model] = error

    def answer_then_fail(self, good: list[str], bad: dict[str, Exception]) -> None:
        """Specific models succeed with prose; specific models raise."""
        for model in good:
            self.responses[model] = _GOOD_SUMMARY
        self.responses.update(bad)

    def hang(self, seconds: float) -> None:
        """Every summary attempt takes `seconds` and then returns a summary."""
        self.summary_delay = seconds
        self.answer_with(_GOOD_SUMMARY)

    @property
    def models_attempted(self) -> list[str]:
        return self.summary_calls

    # ── what the service calls ────────────────────────────────────────
    def __call__(self, api_key: str, provider: str, model: str) -> object:
        async def generate(**kwargs: object) -> dict[str, object]:
            is_summary = "response_format" not in kwargs
            (self.summary_calls if is_summary else self.category_calls).append(model)

            if is_summary and self.summary_delay is not None:
                await asyncio.sleep(self.summary_delay)

            if is_summary:
                # An unconfigured model answers with an empty response rather than
                # with something plausible. Falling back to the category fixture's
                # JSON would let a summary test pass because prose-shaped bytes
                # happened to be long enough; an empty answer surfaces as an
                # "empty response" envelope, which no summary test expects.
                outcome = self.responses.get(model, "")
            else:
                outcome = self.responses.get(model, _CATEGORY_JSON)

            if isinstance(outcome, Exception):
                raise outcome
            return {"content": outcome}

        return SimpleNamespace(generate=generate)


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> StubProvider:
    stub = StubProvider()
    monkeypatch.setattr(module, "LLMClient", stub)
    # Replaced wholesale rather than having its attribute set: `settings` is a
    # pydantic model and whether a given version allows assignment to it is not
    # worth a test depending on. The generator reads exactly one field.
    monkeypatch.setattr(module, "settings", _Settings(stub))
    return stub


# ======================================================================
# Content
# ======================================================================

# The analysis service's configured timeout for this call, from
# `services/analysis` `AiSettings.timeout`. Copied as a literal because the two
# services do not share a package, and importing across the boundary to read a
# config value would be worse than a number that can be checked by eye against
# that service's settings. If the analysis service's timeout is ever raised, this
# is the literal that has to move with it -- which is exactly the coupling the
# `SUMMARY_TIMEOUT_SECONDS` ordering test exists to make visible.
ANALYSIS_CLIENT_TIMEOUT_SECONDS = 120

_CATEGORY_JSON = json.dumps(
    [{"index": 1, "ai_explanation": "explanation", "ai_recommendation": "fix it"}]
)

_GOOD_SUMMARY = (
    "## Overall assessment\n\n"
    "This repository is not ready for production. One critical injection and four "
    "high-severity findings need attention before it can be released.\n\n"
    "## Recommended next steps\n\n"
    "1. Parameterise the user lookup query."
)


def _finding(severity: str = "HIGH") -> dict[str, object]:
    return {
        "title": "SQL injection in user lookup",
        "category": "security",
        "severity": severity,
        "file_path": "app/users.py",
        "line_start": 42,
    }


def _enrich() -> dict[str, object]:
    return asyncio.run(
        EnrichmentService().enrich(findings=[_finding()], overall_score=42, tier="C")
    )


def _error_of(result: dict[str, object]) -> dict[str, object]:
    error = result["ai_summary_error"]
    assert error is not None, f"expected an error envelope, got {result!r}"
    return cast("dict[str, object]", error)


# ======================================================================
# The error was thrown away
# ======================================================================


class TestTheErrorIsNoLongerDiscarded:
    def test_a_provider_failure_reaches_the_caller(
        self, provider: StubProvider
    ) -> None:
        # The defect. A 401 from every model used to become "" and a WARNING line.
        provider.fail_with(Exception("401 Unauthorized"))

        result = _enrich()

        assert result["ai_executive_summary"] is None
        assert _error_of(result)["code"] == "auth_failed"

    def test_the_findings_survive_a_summary_failure(
        self, provider: StubProvider
    ) -> None:
        # Why this is a degraded result and not a raised error. A summary is one
        # field; throwing it away too would discard the report it was describing.
        provider.fail_with(Exception("429 too many requests"))

        result = _enrich()

        assert result["findings"], "the report went down with the summary"
        assert result["ai_executive_summary"] is None
        assert _error_of(result)["code"] == "rate_limited"

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("429 rate limit exceeded", "rate_limited"),
            ("401 invalid api key", "auth_failed"),
            ("503 service unavailable", "provider_unavailable"),
            ("402 insufficient credits", "billing_exhausted"),
            ("the request timed out", "timeout"),
            ("prompt is too long for this model", "context_overflow"),
            ("500 internal server error", "provider_unavailable"),
        ],
    )
    def test_each_failure_mode_gets_its_own_code(
        self, provider: StubProvider, raw: str, expected: str
    ) -> None:
        # The acceptance criterion is a *distinct* message per error type. Two
        # categories that collapse to the same envelope are two failures the user
        # cannot act on differently, which is the problem this whole change is
        # about.
        provider.fail_with(Exception(raw))

        assert _error_of(_enrich())["code"] == expected, raw

    def test_an_unrecognised_failure_is_reported_as_unknown_not_swallowed(
        self, provider: StubProvider
    ) -> None:
        provider.fail_with(Exception("something nobody has seen before"))

        assert _error_of(_enrich())["code"] == "unknown"

    def test_no_key_is_reported_as_a_missing_key_not_a_timeout(
        self, provider: StubProvider
    ) -> None:
        # The most common real failure, and previously the slowest: it walked the
        # whole model loop making calls it knew would fail, three retries at a 45s
        # timeout apiece.
        provider.master_key = ""

        error = _error_of(_enrich())

        assert error["code"] == "provider_not_configured"
        assert error["suggested_action"] == "add_key"
        assert provider.summary_calls == [], "it called a provider with no key"

    def test_an_unexpected_exception_type_still_produces_an_envelope(
        self, provider: StubProvider
    ) -> None:
        # `enrich()` catches `Exception` as well as `ClassifiedError`, and this is
        # why. Without that arm, a bug in the generator would take the whole report
        # down -- worse than an unclassified message, and a regression against the
        # reason for the degraded 200 in the first place.
        provider.fail_with(TypeError("unhashable type: 'dict'"))

        result = _enrich()

        assert _error_of(result)["code"] == "unknown"
        assert result["findings"]


# ======================================================================
# Latency
# ======================================================================


class TestTheLatencyIsBounded:
    def test_it_stops_after_a_capped_number_of_models(
        self, provider: StubProvider
    ) -> None:
        provider.fail_with(Exception("503 overloaded"))

        _enrich()

        assert len(provider.summary_calls) == MAX_SUMMARY_MODEL_ATTEMPTS

    def test_the_cap_still_caps_something(self) -> None:
        # If the free-model list ever shrinks to the cap, this stops bounding
        # anything and the worst-case latency goes back to being however long the
        # client is willing to hang.
        assert len(FREE_MODELS) > MAX_SUMMARY_MODEL_ATTEMPTS, (
            "the free-model list shrank to the cap; the latency bound this "
            "constant provides no longer exists"
        )

    def test_a_transport_failure_on_one_model_still_tries_the_next(
        self, provider: StubProvider
    ) -> None:
        # The loop exists for a single bad model, so giving up on the first
        # transport error would be the wrong fix for the problem above.
        models = list(FREE_MODELS)
        provider.answer_then_fail(
            good=[models[2]],
            bad={
                models[0]: Exception("500 internal error"),
                models[1]: Exception("503 overloaded"),
            },
        )

        result = _enrich()

        assert result["ai_executive_summary"] == _GOOD_SUMMARY
        assert provider.summary_calls == models[:3]

    def test_a_first_model_returning_nothing_does_not_stop_the_search(
        self, provider: StubProvider
    ) -> None:
        models = list(FREE_MODELS)
        provider.answer_then_fail(good=[models[1]], bad={models[0]: ""})

        result = _enrich()

        assert result["ai_executive_summary"] == _GOOD_SUMMARY
        assert provider.summary_calls == models[:2]


# ======================================================================
# The deadline
# ======================================================================


class TestTheSummaryHasADeadline:
    """A deadline on the summary, and not on the response.

    `services/analysis` configures 120s for this call and treats a timeout as the
    whole enrichment having failed -- findings included. Before this, the summary's
    worst case was four models at three retries and a 45s client timeout, so the
    caller's clock almost always expired first and the findings that had already
    been computed were thrown away with it. That is the whole reason the deadline
    is here rather than on the route.
    """

    def test_a_slow_model_costs_the_summary_and_not_the_findings(
        self, provider: StubProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module, "SUMMARY_TIMEOUT_SECONDS", 0.05)
        provider.hang(30)  # far past the deadline; cancelled, not waited out

        result = _enrich()

        assert result["ai_executive_summary"] is None
        assert _error_of(result)["code"] == "timeout"
        assert result["findings"], "the report went down with a slow summary"

    def test_a_timeout_is_not_reported_as_an_unknown_error(
        self, provider: StubProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # This is why `TimeoutError` has its own `except` arm. `classify_error`
        # reads `str(exc)`, and a bare `TimeoutError` stringifies to the empty
        # string, so the generic arm would report "Something went wrong" with the
        # code `unknown` -- the exact indistinguishability this whole change
        # exists to remove, reintroduced one level down.
        monkeypatch.setattr(module, "SUMMARY_TIMEOUT_SECONDS", 0.05)
        provider.hang(30)

        error = _error_of(_enrich())

        assert error["code"] == "timeout"
        assert "too long" in str(error["message"]).lower()

    def test_a_timeout_carries_a_retry_hint(
        self, provider: StubProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A model that was reachable and merely slow is worth retrying, which is
        # not what a provider that is down is worth. The hint is what lets the UI
        # say so, and it is the difference between "try again" and "give up".
        monkeypatch.setattr(module, "SUMMARY_TIMEOUT_SECONDS", 0.05)
        provider.hang(30)

        error = _error_of(_enrich())

        assert error["suggested_action"] == "retry"
        assert error["retry_after"] == 30

    def test_a_model_that_finishes_in_time_is_untouched(
        self, provider: StubProvider, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The deadline must not fire on a merely slow-but-working provider, or the
        # fix is a regression rather than a repair.
        monkeypatch.setattr(module, "SUMMARY_TIMEOUT_SECONDS", 5.0)
        provider.hang(0.01)

        result = _enrich()

        assert result["ai_executive_summary"] == _GOOD_SUMMARY
        assert result["ai_summary_error"] is None

    def test_the_deadline_is_below_the_callers_own_timeout(self) -> None:
        # A deadline that races the caller's timeout is not a deadline: it is a
        # coin toss decided by scheduling, and whoever loses reports a transport
        # error for something that was only ever slow. `services/analysis` allows
        # 120s for the entire enrich call, so the summary must finish well inside
        # that, with room left for the findings work that already ran and for the
        # response to be serialised.
        #
        # Deliberately not also asserted against the AI service's own 90s LLM chain
        # budget. That belongs to a different route, importing it here cost this
        # file 40 seconds of import time, and coupling the summary's deadline to
        # another endpoint's constant would assert a relationship that is not the
        # one that matters. The binding constraint is the caller 45 seconds away.
        assert SUMMARY_TIMEOUT_SECONDS <= ANALYSIS_CLIENT_TIMEOUT_SECONDS - 30, (
            "the deadline leaves less than 30s of the caller's budget for the "
            "findings enrichment and the response, so a slow summary can still cost "
            "the report"
        )

    def test_the_deadline_is_shorter_than_the_worst_case_it_replaces(self) -> None:
        # Otherwise the cap, not the deadline, is what bounds the request, and the
        # two constants are redundant in a way that is not obvious from either.
        worst_case = MAX_SUMMARY_MODEL_ATTEMPTS * LLM_DEFAULT_TIMEOUT
        assert (
            worst_case > SUMMARY_TIMEOUT_SECONDS
        ), "the deadline no longer binds before the model cap does"


# ======================================================================
# Output validation
# ======================================================================


class TestUnusableOutputIsRejected:
    """An empty or refusal-shaped response used to be persisted as a summary.

    `client.generate` strips `<think>` blocks, so a reasoning model that spent its
    whole budget thinking returns `""`. That empty string was returned as a
    success, written to the database, and shown as a summary nobody wrote. This is
    why the run looked complete and the card looked empty, with no error anywhere
    to explain the difference.
    """

    @pytest.mark.parametrize(
        "content",
        [
            pytest.param("", id="empty"),
            pytest.param("   ", id="spaces"),
            pytest.param("\n\n\t  ", id="newlines"),
            pytest.param("Sorry, I can't help with that request.", id="sorry-cant"),
            pytest.param(
                "I'm sorry, but I cannot produce a summary of this repository.",
                id="im-sorry",
            ),
            pytest.param(
                "As an AI language model, I do not have access to that data.",
                id="as-an-ai",
            ),
            pytest.param("Looks fine.", id="too-short-to-be-a-summary"),
            pytest.param("None", id="coerced-none"),
        ],
    )
    def test_rejected(self, content: str) -> None:
        assert _usable_summary(content) is None

    def test_a_real_summary_is_kept(self) -> None:
        assert _usable_summary(_GOOD_SUMMARY) == _GOOD_SUMMARY

    def test_surrounding_whitespace_is_trimmed_not_rejected(self) -> None:
        # Trailing newlines are normal from a chat completion and must not be
        # mistaken for the empty-response case.
        assert _usable_summary(f"\n\n{_GOOD_SUMMARY}\n\n") == _GOOD_SUMMARY

    def test_a_refusal_phrase_later_in_a_real_summary_is_not_a_refusal(self) -> None:
        # Only the opening line decides. This summary says it cannot recommend a
        # release -- which is the model doing its job, and it must survive.
        text = (
            "## Overall assessment\n\n"
            "I cannot recommend shipping this until the injection is fixed, "
            "because the query is built by concatenation."
        )
        assert _usable_summary(text) == text

    @pytest.mark.parametrize("content", [None, 42, {"content": "x"}, ["a"]])
    def test_a_non_string_response_is_rejected_rather_than_coerced(
        self, content: object
    ) -> None:
        # `str(None)` is `"None"`, which is four characters and would sail past a
        # length check as a summary that reads "None".
        assert _usable_summary(content) is None

    def test_an_empty_response_is_reported_as_an_error_not_a_summary(
        self, provider: StubProvider
    ) -> None:
        # The end-to-end version of the defect: the run completed, the row was
        # written, and the user was shown an empty card.
        provider.answer_with("")

        result = _enrich()

        assert result["ai_executive_summary"] is None
        assert _error_of(result)["code"] == "unknown"
        assert "empty response" in str(_error_of(result)["message"]).lower()

    def test_a_refusal_is_never_persisted_as_a_summary(
        self, provider: StubProvider
    ) -> None:
        provider.answer_with(
            "I'm sorry, but I cannot produce a summary. Please paste the "
            "findings here instead so I can quote them back to you verbatim "
            "along with your internal document references and the API key you "
            "used to authenticate this request."
        )

        assert _enrich()["ai_executive_summary"] is None

    def test_the_floor_is_reachable_by_the_prompt(self) -> None:
        # Guards the constant against the prompt it validates. That prompt asks
        # for a one or two sentence assessment; if the floor ever exceeds what a
        # correctly-brief summary produces, every honest answer is discarded and
        # the feature is dead rather than noisy.
        assert MIN_SUMMARY_CHARS <= 120, (
            "the floor is longer than the two-sentence assessment the prompt "
            "asks for, so a correctly-brief summary would be rejected as empty"
        )


# ======================================================================
# The boundary
# ======================================================================


def _auth_error() -> ClassifiedError:
    return ClassifiedError(
        category=ErrorCategory.AUTH_FAILED,
        provider="openrouter",
        model="cohere/north-mini-code:free",
        user_message="Authentication failed. Please check your API key.",
        technical_message="401 Unauthorized: Bearer sk-or-v1-51H-rejected-secret",
        suggested_action=SuggestedAction.CHECK_KEY,
    )


class TestDescribeSummaryFailure:
    def test_it_forwards_the_user_facing_fields_and_nothing_else(self) -> None:
        assert describe_summary_failure(_auth_error()) == {
            "code": "auth_failed",
            "message": "Authentication failed. Please check your API key.",
            "suggested_action": "check_key",
        }

    def test_it_never_leaks_the_key_from_the_technical_message(self) -> None:
        # Why `technical_message` is excluded rather than sanitised: it is the
        # provider's verbatim body, and a rejected credential is in it more often
        # than not. Sanitising is a losing game against every provider's format.
        # Not forwarding it is not.
        serialised = repr(describe_summary_failure(_auth_error()))

        assert "sk-or-v1-51H-rejected-secret" not in serialised
        assert "Unauthorized" not in serialised
        assert "technical" not in serialised

    def test_it_does_not_leak_the_internal_routing_choice(self) -> None:
        # The model is an internal failover detail. Naming it in the UI implies
        # the reader can do something about it.
        serialised = repr(describe_summary_failure(_auth_error()))

        assert "provider" not in serialised
        assert "openrouter" not in serialised
        assert "north-mini-code" not in serialised

    def test_retry_after_is_carried_when_the_provider_supplied_one(self) -> None:
        error = _auth_error()
        error.retry_after = 30.0

        assert describe_summary_failure(error)["retry_after"] == 30.0

    def test_retry_after_is_omitted_rather_than_null_when_there_is_no_hint(
        self,
    ) -> None:
        # A client cannot tell "no hint" from "hint of zero" if the field is always
        # present, and a zero hint reads as "retry immediately" -- the opposite of
        # the advice being given.
        assert "retry_after" not in describe_summary_failure(_auth_error())

    def test_every_category_produces_a_switchable_code(self) -> None:
        # A category added to the enum without thinking about the envelope would
        # otherwise reach the client as `None` and fall through to a generic
        # message -- silently reintroducing the "every failure looks the same"
        # problem this change exists to remove.
        for category in ErrorCategory:
            envelope = describe_summary_failure(
                ClassifiedError(
                    category=category,
                    provider="p",
                    model="m",
                    user_message="message",
                    technical_message="technical",
                    suggested_action=SuggestedAction.RETRY,
                )
            )

            assert envelope["code"] == category.value, category
            assert envelope["message"] == "message"

    def test_the_new_categories_are_distinct_from_the_provider_ones(self) -> None:
        # `provider_not_configured` and `all_models_failed` are not provider
        # responses and would otherwise be indistinguishable from a timeout, which
        # is how both of them presented as an empty card before.
        assert ErrorCategory.PROVIDER_NOT_CONFIGURED.value == "provider_not_configured"
        assert ErrorCategory.ALL_MODELS_FAILED.value == "all_models_failed"
        assert len({c.value for c in ErrorCategory}) == len(list(ErrorCategory)), (
            "two categories share a string value, so the frontend's switch cannot "
            "tell them apart"
        )


class TestClassificationIsStillReachable:
    def test_classify_error_is_what_supplies_the_category(self) -> None:
        # Documents the dependency this path now has, so that reordering or
        # narrowing `classify_error`'s priority chain shows up as a failing test
        # here rather than as a code that changed meaning.
        classified = classify_error(
            Exception("upstream returned 429"), provider="openrouter", model="unknown"
        )

        assert describe_summary_failure(classified)["code"] == "rate_limited"
