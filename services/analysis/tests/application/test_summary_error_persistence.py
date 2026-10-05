"""Pin that the reason a summary is missing survives all the way to the guide.

The AI service produced `ai_summary_error` and the analysis service read the
response with

    ai_executive_summary = str(result.get("ai_executive_summary", ""))

which turned the service's `None` straight back into `""`, and then branched on
that. So a summary that failed, a summary nobody asked for, and a summary the AI
service never attempted were one event: an empty string, a WARNING log, and
nothing in any response a browser could read. 548 tests passed throughout.

Three separate things had to be true for the reason to reach a user, and each was
independently capable of losing it. These tests are arranged as those three
things, because a test that only checked the first would still pass with the
second and third reverted:

  1. `_readable_summary_error` narrows the envelope to what is safe to serve.
  2. `handle_stage_ai_enrich` reads it off the response without re-coercing the
     summary to a string, and writes it beside the summary.
  3. `handle_re_generate_guide` preserves it across a regeneration, rather than
     nulling it through `merge()`.

`handle_stage_ai_enrich` and `handle_re_generate_guide` are reached through the
handler module rather than imported by name, so running this file against pre-fix
source produces real test failures instead of a collection-time ImportError that
would hide every other defect here behind one error.

**Stated precisely, because it matters:** against pre-fix source, sections 1 and 3
fail through an explicit `pytest.fail` naming the missing helper, while section 2
fails with an `AttributeError` -- the pre-fix handler does not call
`_readable_summary_error` at all, so there is nothing for the test to intercept.
All 24 tests fail, and none is vacuous, but section 2's four tests do not produce
the assertion failures on the summary-vs-error branch that they read as if they
did. Reverting only the `str(...)` coercion inside the handler while keeping the
helper would be what would show that branch directly.
"""

from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest

from app.application.analysis import handler as handler_mod
from app.application.analysis.commands import ProcessStageCommand
from app.domain.entities.finding import Finding
from app.infrastructure.db.unit_of_work import UnitOfWork

_ERROR = {
    "code": "rate_limited",
    "message": "AI service is busy. Please try again shortly.",
    "suggested_action": "wait",
    "retry_after": 30,
}


def _narrow(raw: object) -> dict[str, object] | None:
    """Call the narrowing helper by module attribute, not by imported name."""
    narrow = getattr(handler_mod, "_readable_summary_error", None)
    if narrow is None:  # pragma: no cover - the pre-fix shape
        pytest.fail(
            "_readable_summary_error does not exist; the envelope is unvalidated"
        )
    return cast("dict[str, object] | None", narrow(raw))


# ======================================================================
# 1. The envelope is narrowed before it is stored
# ======================================================================


class TestTheEnvelopeIsNarrowed:
    def test_a_well_formed_envelope_passes_through(self) -> None:
        assert _narrow(_ERROR) == _ERROR

    def test_a_provider_field_is_dropped_rather_than_sanitised(self) -> None:
        # The AI service already builds the envelope from four named fields, so
        # this field should never arrive. It is tested anyway because this is a
        # second boundary crossing: two services that deploy independently, and
        # the column this lands in is served to browsers by the guide endpoint.
        #
        # Dropping is the right response to an unexpected key rather than
        # accepting it. A blacklist protects against the leaks somebody already
        # thought of; a whitelist protects against the ones nobody has yet.
        assert _narrow({**_ERROR, "provider": "openrouter"}) == _ERROR

    def test_a_technical_message_is_never_stored(self) -> None:
        # This is the one that matters. `technical_message` is the provider's
        # verbatim response body, and on an auth failure it contains the rejected
        # key. A row in `enterprise_guides` is readable through `GET /guides/...`.
        stored = _narrow(
            {
                **_ERROR,
                "technical_message": ("401 invalid api key: sk-or-v1-REJECTED-abc123"),
            }
        )

        assert stored == _ERROR
        assert "sk-or-v1-REJECTED-abc123" not in str(stored)

    def test_a_model_name_is_dropped(self) -> None:
        # Naming a model in the UI implies the reader can act on choosing a
        # different one. They cannot; routing is internal.
        assert _narrow({**_ERROR, "model": "some/very:free"}) == _ERROR

    def test_a_blank_code_is_not_a_reason(self) -> None:
        # `None` means "no reason was reported", which is different from a
        # reported reason. A blank code with a real message is neither, and
        # storing it would put a confident-sounding wrong answer where the truth
        # is missing.
        assert _narrow({**_ERROR, "code": "   "}) is None
        assert _narrow({**_ERROR, "code": ""}) is None

    def test_a_missing_message_is_not_a_reason(self) -> None:
        # A code with no message cannot be rendered. The UI has one slot for the
        # explanation, and this would either show nothing or show the code twice.
        assert _narrow({k: v for k, v in _ERROR.items() if k != "message"}) is None
        assert _narrow({**_ERROR, "message": ""}) is None

    @pytest.mark.parametrize(
        "raw",
        [None, "", "rate_limited", 42, [], [{"code": "rate_limited"}]],
        ids=["null", "empty-string", "bare-string", "number", "list", "list-of-one"],
    )
    def test_a_payload_that_is_not_an_envelope_is_no_reason(self, raw: object) -> None:
        # Reachable: the AI service is a separate deployment and a version skew
        # or a proxy in between can put anything here. None is the honest answer
        # for all of them.
        assert _narrow(raw) is None

    def test_an_absent_action_is_omitted_rather_than_nulled(self) -> None:
        # Matches the envelope upstream. A client cannot tell "no hint" from "a
        # hint of zero", and a zero hint reads as "retry immediately" -- the
        # opposite of the advice a missing action implies.
        stored = _narrow({k: v for k, v in _ERROR.items() if k != "suggested_action"})

        assert stored is not None
        assert "suggested_action" not in stored

    def test_a_numeric_retry_hint_survives(self) -> None:
        stored = _narrow(_ERROR)

        assert stored is not None
        assert stored["retry_after"] == 30

    def test_a_boolean_retry_hint_is_not_a_number(self) -> None:
        # `isinstance(True, int)` is True in Python, so without the bool guard a
        # stray `true` would be stored as `1` -- which reads as "retry in one
        # second" and is exactly the misreading the omission was meant to avoid.
        assert _narrow({**_ERROR, "retry_after": True}) is not None
        assert "retry_after" not in cast(
            "dict[str, object]", _narrow({**_ERROR, "retry_after": True})
        )

    def test_a_non_numeric_retry_hint_is_omitted(self) -> None:
        # "30 seconds" would be stored as a string in a column the UI renders as
        # a number, and the UI is the only reader.
        stored = _narrow({**_ERROR, "retry_after": "30 seconds"})

        assert stored is not None
        assert "retry_after" not in stored

    def test_no_forwarded_key_is_outside_the_documented_set(self) -> None:
        # The negative assertion about every input, rather than a check that the
        # four expected keys arrived. `set(...)` over a hostile envelope of
        # unexpected keys is the property worth pinning; "the expected four are
        # present" would pass just as well on an implementation that also
        # forwarded everything else.
        hostile = {
            **_ERROR,
            "provider": "openrouter",
            "model": "some/model",
            "technical_message": "key=sk-or-v1-REJECTED",
            "traceback": 'File "/srv/app/x.py", line 1',
            "api_key": "sk-or-v1-REJECTED",
            "headers": {"Authorization": "Bearer sk-or-v1-REJECTED"},
            "nested": {"raw": "anything"},
        }

        stored = _narrow(hostile)

        assert stored is not None
        assert set(stored) <= {"code", "message", "suggested_action", "retry_after"}
        assert "sk-or-v1-REJECTED" not in str(stored)


# ======================================================================
# 2. The stage handler does not re-coerce the summary away
# ======================================================================


class _GuideRecorder:
    """Captures what `save()` was handed, which is what reaches the row."""

    def __init__(self, existing: dict[str, object] | None) -> None:
        self.existing = existing
        self.saves: list[dict[str, object]] = []

    async def get_by_job(self, job_id: object) -> dict[str, object] | None:
        if self.existing is None:
            return None
        return {**self.existing, "job_id": job_id}

    async def save(self, guide: dict[str, object]) -> None:
        self.saves.append(dict(guide))

    def last(self) -> dict[str, object]:
        assert self.saves, "nothing was saved"
        return self.saves[-1]


class _UnitOfWork:
    """Only the repositories `handle_stage_ai_enrich` touches."""

    def __init__(self, guide: _GuideRecorder, findings: list[object]) -> None:
        self.enterprise_guides = guide
        self.findings = _Findings(findings)
        self.jobs = _Jobs()

    findings: _Findings
    jobs: _Jobs


class _Findings:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows
        self.updates: list[dict[str, object]] = []

    async def update_ai_fields(self, **kwargs: object) -> None:
        self.updates.append(kwargs)


class _Jobs:
    def __init__(self) -> None:
        self.updates: list[dict[str, object]] = []

    async def get_by_id(self, job_id: object) -> dict[str, object]:
        return {"id": job_id}

    async def update_status(
        self, job_id: object, status: object, **kwargs: object
    ) -> None:
        self.updates.append({"job_id": job_id, "status": status, **kwargs})


class _Finding:
    """One finding, in the shape the handler reads."""

    def __init__(self, title: str, file_path: str) -> None:
        self.id = uuid4()
        self.title = title
        self.category = "security"
        self.severity = "HIGH"
        self.description = "d"
        self.recommendation = "r"
        self.file_path = file_path
        self.line_start = 1
        self.line_end = 2
        self.code_snippet = "x = 1"


async def _run_enrich(
    monkeypatch: pytest.MonkeyPatch, response: dict[str, object], guide: _GuideRecorder
) -> dict[str, object] | None:
    """Run the real handler over a stubbed AI client that returns `response`."""

    class _Client:
        async def enrich_findings(self, **kwargs: object) -> dict[str, object]:
            return response

    monkeypatch.setattr(
        "app.infrastructure.ai.enrichment_client.AiEnrichmentClient", _Client
    )

    finding = _Finding("SQL injection", "app/users.py")
    return await handler_mod.handle_stage_ai_enrich(
        ProcessStageCommand(job_id=uuid4(), stage="ai_enrich"),
        # `UnitOfWork` in the signature, `_UnitOfWork` here: a stand-in for it,
        # holding only the three repositories the handler reaches. A cast rather
        # than a subclass because the real one builds a session and a set of
        # repositories this test has no use for.
        cast("UnitOfWork", _UnitOfWork(guide, [finding])),
        [cast("Finding", finding)],
    )


class TestTheStageHandlerPersistsTheReason:
    async def test_a_failed_summary_writes_the_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        guide = _GuideRecorder({"id": uuid4()})

        await _run_enrich(
            monkeypatch,
            {"findings": [], "ai_executive_summary": None, "ai_summary_error": _ERROR},
            guide,
        )

        written = guide.last()
        assert written["ai_summary_error"] == _ERROR
        # And not a summary: `None` must not have been turned back into `""`.
        assert written.get("ai_executive_summary") is None

    async def test_a_missing_reason_is_stored_as_none_not_invented(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The AI service said nothing. Writing a synthetic code here would put a
        # confident wrong answer where the truth is absent -- the same failure as
        # the original bug, in a more respectable-looking column.
        guide = _GuideRecorder({"id": uuid4()})

        await _run_enrich(
            monkeypatch, {"findings": [], "ai_executive_summary": None}, guide
        )

        assert guide.last()["ai_summary_error"] is None

    async def test_a_successful_summary_clears_an_earlier_reason(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The re-enrich path: a first attempt failed and recorded why, a second
        # succeeded. Leaving the error would show a reader a summary and the
        # reason it could not be written, at the same time.
        guide = _GuideRecorder({"id": uuid4(), "ai_summary_error": dict(_ERROR)})

        await _run_enrich(
            monkeypatch,
            {
                "findings": [],
                "ai_executive_summary": "## Assessment\n\nNot ready.",
                "ai_summary_error": None,
            },
            guide,
        )

        written = guide.last()
        assert written["ai_summary_error"] is None
        assert written["ai_executive_summary"] == "## Assessment\n\nNot ready."

    async def test_an_empty_string_summary_is_not_treated_as_a_summary(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The exact coercion the old line performed. The AI service's
        # `AiSummaryError` validator already refuses to emit `""`, so this cannot
        # happen today -- but a blank string is truthy-adjacent enough that a
        # future change could reintroduce it, and the branch is the thing under
        # test.
        guide = _GuideRecorder({"id": uuid4()})

        await _run_enrich(
            monkeypatch,
            {"findings": [], "ai_executive_summary": "", "ai_summary_error": _ERROR},
            guide,
        )

        assert guide.last()["ai_summary_error"] == _ERROR


# ======================================================================
# 3. A regeneration does not null out the recorded reason
# ======================================================================


class TestRegenerationPreservesTheReason:
    def test_a_regenerated_guide_carries_the_error_forward(self) -> None:
        # `guide.to_dict()` knows nothing of `ai_summary_error`, so leaving the
        # key out hands `merge()` an instance with the column unset -- and the
        # recorded failure is nulled. Losing the reason is the bug this column
        # exists to fix, so losing it here would be the same defect one layer
        # down, with the column present to make it look solved.
        existing: dict[str, object] = {
            "id": uuid4(),
            "ai_executive_summary": "## Assessment\n\nStale.",
            "ai_summary_error": dict(_ERROR),
        }

        preserved = _preserved_for_regeneration(existing)

        assert preserved["ai_summary_error"] == _ERROR
        # The summary too: regeneration does not produce one, so dropping it here
        # would lose a summary the user already paid for.
        assert preserved["ai_executive_summary"] == "## Assessment\n\nStale."

    def test_a_guide_with_no_recorded_error_does_not_gain_one(self) -> None:
        # The other direction. A run that never had a failure must not acquire an
        # error object on regeneration -- `save()` builds a model from the dict,
        # so an invented key would write a fabricated row value.
        existing: dict[str, object] = {"id": uuid4(), "ai_executive_summary": "s"}

        preserved = _preserved_for_regeneration(existing)

        assert "ai_summary_error" not in preserved

    def test_an_empty_error_dict_is_still_carried_across(self) -> None:
        # `is not None` rather than truthiness. `{}` cannot be produced by
        # `_readable_summary_error`, which requires a code and a message, so this
        # only arises from a hand-written row or a future change. Carrying it is
        # still correct: `None` is the only value that means "no error", and
        # treating `{}` as absent is how an error would silently become an
        # invented one.
        existing: dict[str, object] = {"id": uuid4(), "ai_summary_error": {}}

        assert _preserved_for_regeneration(existing)["ai_summary_error"] == {}


def _preserved_for_regeneration(existing: dict[str, object]) -> dict[str, object]:
    """Call the real preservation helper by module attribute.

    `handle_re_generate_guide` itself needs a complete analysis dataset and a real
    `EnterpriseGuide` to reach the four lines that matter, so what is pinned here
    is the *decision* -- which keys survive a regeneration -- extracted as the
    helper the handler calls. That decision is the part that can silently regress:
    the helper is what `handle_re_generate_guide` uses, so a change to one without
    the other shows up as a failing test rather than as a nulled column.
    """
    carry = getattr(handler_mod, "_carried_across_regeneration", None)
    if carry is None:  # pragma: no cover - the pre-fix shape
        pytest.fail(
            "_carried_across_regeneration does not exist; a regenerated guide "
            "carries nothing across, so save() nulls both columns"
        )
    return cast("dict[str, object]", carry(existing))
