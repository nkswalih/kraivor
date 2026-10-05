"""Tests for how per-engine state reaches the job row.

Every test here corresponds to a defect that shipped and was fixed. The 460-test
suite passed identically before and after those fixes, which is the whole reason
they survived: nothing asserted *when* or *what* got written to
`engine_statuses`.

The tests are deliberately written against the database write rather than
against the helper that performs it, so they fail for the original reason rather
than because an internal function was renamed.

  1. An engine that finished still read `running` until an unrelated stage began.
  2. A failed run left every engine reading `running`/`pending` on a dead job.
  3. A job that failed at 90% rendered as `0% - failed`.
  4. A fully completed job reported 5 of its 9 engines.
  5. Legacy rows holding a bare status string no longer serialise.
"""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ClauseElement

from app.api.schemas import jobs as jobs_schemas
from app.application.analysis import handler as handler_mod
from app.application.analysis.commands import ProcessStageCommand, StartAnalysisCommand
from app.application.analysis.handler import (
    handle_analysis_failure,
    handle_stage_finalize,
)
from app.application.tasks import pipeline
from app.application.tasks.pipeline import _run_pipeline
from app.core.constants import EngineStateMap
from app.core.engines import ALL_ENGINES, stage_to_engine_keys
from app.domain.contracts.storage import AbstractStorage
from app.domain.entities.score import Score
from app.infrastructure.db.repositories.analysis_job import JobRepository
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.messaging.producer import EventProducer

# The helpers these tests exercise were introduced *by* the fixes being tested.
# They are reached through their modules rather than imported by name so that
# running this file against pre-fix source produces real assertion failures
# instead of a collection-time ImportError, which would hide every other defect
# in the file behind one error.

# One engine's row, as written to the JSON column. `object` rather than `Any`:
# the project's mypy runs with `disallow_any_explicit`, and the values are
# heterogeneous anyway (status strings, ISO timestamps, error text).
EngineRow = dict[str, object]
EngineMap = dict[str, EngineRow]

# A stage callable: the shared-state dict plus whatever stage-specific arguments
# the pipeline passes. Spelled with an unpacked tuple rather than `...` because
# the project's mypy runs with `disallow_any_explicit`.
_StageStub = Callable[[dict[str, object], *tuple[object, ...]], Awaitable[None]]

# ======================================================================
# Harness: capture every write to the job row
# ======================================================================


class _WriteRecorder:
    """Records the bound parameters of every UPDATE the pipeline issues.

    `_push_progress` and `_push_engine_statuses` both import
    `async_session_factory` lazily inside the function body, so patching the
    module attribute intercepts both. Reading the compiled statement's params
    gives the literal column values, which is what makes it possible to assert
    on *which columns* a write touched - the point of the narrow engine-status
    update.

    `events` interleaves writes with stage boundaries in a single ordered list,
    so a test can ask "what was written between these two stages" rather than
    only what the final value happened to be.
    """

    def __init__(self) -> None:
        self.params: list[dict[str, object]] = []
        self.events: list[tuple[str, object]] = []

    def note(self, kind: str, payload: object) -> None:
        self.events.append((kind, payload))

    def session_factory(self) -> _FakeSession:
        return _FakeSession(self)

    def engine_maps(self) -> list[EngineMap]:
        """Only the writes that actually set engine_statuses."""
        return [
            cast(EngineMap, p["engine_statuses"])
            for p in self.params
            if "engine_statuses" in p
        ]


class _FakeSession:
    def __init__(self, recorder: _WriteRecorder) -> None:
        self._recorder = recorder

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def execute(self, stmt: ClauseElement) -> None:
        params = dict(stmt.compile().params)
        self._recorder.params.append(params)
        if "engine_statuses" in params:
            self._recorder.note("write", params["engine_statuses"])

    async def commit(self) -> None:
        return None


class _FakeProducer:
    """Swallows progress/completion events so no Redis is needed."""

    async def publish(self, event: object) -> None:
        return None


def _install_recorder(monkeypatch: pytest.MonkeyPatch) -> _WriteRecorder:
    recorder = _WriteRecorder()
    monkeypatch.setattr(
        "app.infrastructure.db.session.async_session_factory", recorder.session_factory
    )
    monkeypatch.setattr(pipeline, "EventProducer", _FakeProducer)
    return recorder


def _stub_stages(
    monkeypatch: pytest.MonkeyPatch,
    recorder: _WriteRecorder,
    boom_on: str | None = None,
) -> None:
    """Replace every stage with a recorder, optionally raising on one stage.

    `_run_pipeline` builds its stage tuple from module globals when it runs, so
    patching the attributes here is enough to take over the whole loop without
    the test depending on what any real stage does. Stage boundaries are noted
    on the same event stream the database writes use, which is what lets the
    tests above reason about what was written *between* two stages.
    """

    def _make(name: str) -> _StageStub:
        async def _stage(state: dict[str, object], *args: object) -> None:
            recorder.note("stage_end", name)
            if boom_on == name:
                raise RuntimeError(f"{name} exploded")

        return _stage

    for name in (
        "start",
        "clone",
        "churn",
        "parse",
        "rules",
        "save_findings",
        "dead_code",
        "errors",
        "reliability",
        "maintainability",
        "devops",
        "perf",
        "simulation",
        "score",
        "guide_gen",
        "ai_enrich",
        "finalize",
    ):
        monkeypatch.setattr(pipeline, f"_stage_{name}", _make(name))


def _cmd() -> StartAnalysisCommand:
    return StartAnalysisCommand(
        repo_id=uuid4(),
        workspace_id=uuid4(),
        triggered_by=uuid4(),
        trigger_type="manual",
        repo_url="https://github.com/example/repo",
    )


def _text(value: object) -> str:
    """Narrow a JSON column value to text.

    The engine map is `object`-typed because its values are heterogeneous, but
    every containment or ordering assertion here is about a string field. The
    timestamps are ISO-8601 in one fixed format, so they also compare correctly
    as plain strings.
    """
    return cast(str, value)


def _engine_state(status: str, error: str = "") -> EngineRow:
    return {
        "status": status,
        "started_at": "2026-01-01T00:00:00+00:00",
        "ended_at": "2026-01-01T00:00:05+00:00",
        "error": error,
    }


def _first_write_where(
    recorder: _WriteRecorder, predicate: Callable[[EngineMap], bool]
) -> int | None:
    """Index of the first recorded write whose engine map satisfies `predicate`."""
    return next(
        (
            i
            for i, (kind, payload) in enumerate(recorder.events)
            if kind == "write" and predicate(cast(EngineMap, payload))
        ),
        None,
    )


# ======================================================================
# 1. Engine completion must be persisted when the engine finishes
# ======================================================================


class TestEngineCompletionIsPersistedEagerly:
    """Defect: the only write of `completed` was the *next* stage's progress
    push, so the API served every engine one stage stale.

    The frontend polls the job every 2s. A stage that takes a minute therefore
    showed a minute of `running` after the engine had already finished.
    """

    def test_every_stage_is_written_as_completed_before_the_next_stage_starts(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The core guarantee, checked for all nine engines rather than a sample.

        Asserting only on *what* a write contains is not enough: the next stage's
        progress push also reports the finished engines as `completed`, so a
        naive check passes even with the bug present. What distinguishes the fix
        is *when* the write happens. The write that records stage N completing
        must land before any write that shows a later stage's engine as running.

        Before the fix, those were the same write, so the completion of stage N
        was only ever observable at the moment stage N+1 announced itself.
        """
        recorder = _install_recorder(monkeypatch)
        _stub_stages(monkeypatch, recorder)

        state: dict[str, object] = {"job_id": uuid4()}
        asyncio.run(_run_pipeline(_cmd(), state))

        write_indices = [
            i for i, (kind, _) in enumerate(recorder.events) if kind == "write"
        ]
        assert write_indices, "the pipeline never wrote engine_statuses"

        stage_ends = [
            cast(str, payload)
            for kind, payload in recorder.events
            if kind == "stage_end"
        ]
        checked: list[str] = []

        for position, stage_name in enumerate(stage_ends):
            engine_ids = list(stage_to_engine_keys().get(stage_name, []))
            if not engine_ids:
                continue
            # Recorded whether or not there is a later engine to compare
            # against, so this also proves every engine is stage-owned.
            checked.extend(engine_ids)

            later_engines = [
                engine
                for later_stage in stage_ends[position + 1 :]
                for engine in stage_to_engine_keys().get(later_stage, [])
            ]
            if not later_engines:
                # The final engine-owning stage; nothing follows to be stale about.
                continue

            def _all_completed(m: EngineMap, ids: list[str] = engine_ids) -> bool:
                return all((m.get(x) or {}).get("status") == "completed" for x in ids)

            def _any_running(m: EngineMap, ids: list[str] = later_engines) -> bool:
                return any((m.get(x) or {}).get("status") == "running" for x in ids)

            completed_at = _first_write_where(recorder, _all_completed)
            later_started_at = _first_write_where(recorder, _any_running)

            assert (
                completed_at is not None
            ), f"{stage_name}'s engines never reached `completed` in any write"
            assert (
                later_started_at is not None
            ), f"no write ever showed a stage after {stage_name} starting"
            assert completed_at < later_started_at, (
                f"{stage_name}'s engines were first recorded as completed in the "
                "same write that started a later stage's engine, so the API "
                "reported them as still running until unrelated work began"
            )

        assert sorted(checked) == sorted(
            ALL_ENGINES
        ), "not every catalogue engine is owned by a stage the pipeline runs"

    def test_a_completed_engine_carries_a_real_end_timestamp(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The row must say *when* an engine finished, not just that it did."""
        recorder = _install_recorder(monkeypatch)
        _stub_stages(monkeypatch, recorder)

        state: dict[str, object] = {"job_id": uuid4()}
        asyncio.run(_run_pipeline(_cmd(), state))

        for engine_map in recorder.engine_maps():
            for engine_id, row in engine_map.items():
                if row["status"] != "completed":
                    continue
                assert row["started_at"], f"{engine_id} completed with no start"
                assert row["ended_at"], f"{engine_id} completed with no end"
                assert _text(row["ended_at"]) >= _text(
                    row["started_at"]
                ), f"{engine_id} ended before it started"
                assert row["error"] == "", f"{engine_id} completed with an error"

    def test_the_completion_write_touches_only_the_engine_column(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A transition must not rewrite status/progress.

        `_push_progress` rewrites those columns too, and they do not change when
        an engine finishes. Writing the whole row on every transition risks
        clobbering a concurrent stage write, so the engine update is narrow.
        """
        recorder = _install_recorder(monkeypatch)
        _stub_stages(monkeypatch, recorder)

        state: dict[str, object] = {"job_id": uuid4()}
        state["engine_statuses"] = {"security": "completed"}
        state["_engine_meta"] = {"security": {"started_at": "x", "ended_at": "y"}}

        asyncio.run(pipeline._persist_engine_statuses(state))

        engine_writes = [
            p
            for p in recorder.params
            if set(p.keys()) == {"engine_statuses", "id", "executemany"}
        ] or [p for p in recorder.params if "engine_statuses" in p]
        assert engine_writes, "nothing was written"
        for params in engine_writes:
            assert "status" not in params
            assert "progress_pct" not in params
            assert "progress_message" not in params

    def test_every_known_engine_appears_in_the_first_write(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The row must describe all 9 engines, not just the ones running yet.

        Otherwise a reader cannot tell "not started" from "does not exist", which
        is how three working engines looked permanently absent.
        """
        recorder = _install_recorder(monkeypatch)
        _stub_stages(monkeypatch, recorder)

        state: dict[str, object] = {"job_id": uuid4()}
        asyncio.run(_run_pipeline(_cmd(), state))

        first = recorder.engine_maps()[0]
        assert set(first) == set(ALL_ENGINES)
        for key in ("dead_code", "error_detection", "churn"):
            assert key in first, f"{key} missing from the persisted engine map"


# ======================================================================
# 2. A failed run must record which engines failed
# ======================================================================


class _RecordingJobsRepo:
    """Captures the arguments `update_status` was called with.

    `status_calls` is the useful one: it is the exact keyword set the caller
    chose to write, which is how "did the failure path pass progress_pct" is
    answered. `**kwargs: object` rather than `Any` for the same mypy reason as
    above.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def update_status(self, *args: object, **kwargs: object) -> None:
        self.calls.append((args, kwargs))

    async def get_by_id(self, job_id: UUID) -> dict[str, object]:
        return {"repo_id": uuid4(), "workspace_id": uuid4()}


class _FakeUow:
    def __init__(self, jobs: _RecordingJobsRepo) -> None:
        self.jobs = jobs


class TestFailureCarriesEngineStatuses:
    """Defect: the pipeline set failed engines in memory, but nothing carried
    that map to the row. Every engine on a halted job still read
    `running`/`pending`, which reads as "still working" for a job that is dead.
    """

    def test_failed_engines_are_persisted(self) -> None:
        jobs = _RecordingJobsRepo()
        uow = _FakeUow(jobs)
        job_id = uuid4()

        statuses: EngineStateMap = {
            "security": _engine_state("completed"),
            "dead_code": _engine_state(
                "failed", "dead_code: RuntimeError - detector blew up"
            ),
            "error_detection": {"status": "pending", "error": ""},
        }

        asyncio.run(
            handle_analysis_failure(
                job_id=job_id,
                stage="dead_code",
                error_message="detector blew up",
                uow=cast("UnitOfWork", uow),
                producer=cast("EventProducer", _FakeProducer()),
                engine_statuses=statuses,
            )
        )

        assert jobs.calls, "update_status was never called"
        _, kwargs = jobs.calls[0]
        persisted = cast(EngineMap, kwargs["engine_statuses"])

        assert persisted["dead_code"]["status"] == "failed"
        assert "detector blew up" in _text(persisted["dead_code"]["error"])
        # Engines that already finished must not be relabelled by the failure.
        assert persisted["security"]["status"] == "completed"
        # Engines never reached keep their real state rather than inheriting the
        # failure.
        assert persisted["error_detection"]["status"] == "pending"

    def test_the_repository_does_not_rewind_progress_when_omitted(self) -> None:
        """The same defect, caught where it actually lived.

        The handler test above only proves the handler no longer *passes*
        progress_pct. The bug was one level down: `update_status` defaulted
        `progress_pct` to 0 and always wrote it, so any caller that omitted the
        argument silently reset the bar. That is the property worth pinning, and
        it is invisible from the handler.
        """
        recorder = _WriteRecorder()
        repo = JobRepository(cast("AsyncSession", _FakeSession(recorder)))

        asyncio.run(
            repo.update_status(
                uuid4(), "failed", progress_message="Failed at stage: simulation"
            )
        )

        assert recorder.params, "update_status wrote nothing"
        params = recorder.params[0]
        assert "progress_pct" not in params, (
            f"omitting progress_pct still wrote {params.get('progress_pct')!r}; "
            "a job that failed at 90% would render as 0%"
        )
        # The columns the caller did ask for must still be written.
        assert params["status"] == "failed"
        assert params["progress_message"] == "Failed at stage: simulation"

    def test_the_repository_writes_progress_when_given(self) -> None:
        """Guards the fix against over-correcting into "never writes progress"."""
        recorder = _WriteRecorder()
        repo = JobRepository(cast("AsyncSession", _FakeSession(recorder)))

        asyncio.run(
            repo.update_status(
                uuid4(), "running", progress_pct=45, progress_message="halfway"
            )
        )

        params = recorder.params[0]
        assert params["progress_pct"] == 45
        assert params["progress_message"] == "halfway"

    def test_the_repository_writes_engines_when_given(self) -> None:
        """Same, for the engine map: omitted leaves it alone, supplied writes it."""
        recorder = _WriteRecorder()
        repo = JobRepository(cast("AsyncSession", _FakeSession(recorder)))
        statuses: EngineStateMap = {"security": _engine_state("completed")}

        asyncio.run(repo.update_status(uuid4(), "running", engine_statuses=statuses))
        assert recorder.params[0]["engine_statuses"] == statuses

        recorder.params.clear()
        asyncio.run(repo.update_status(uuid4(), "running"))
        assert "engine_statuses" not in recorder.params[0]

    def test_failure_does_not_rewind_progress(self) -> None:
        """Defect: `update_status` defaulted `progress_pct` to 0, and the failure
        path relied on that default.

        A job that failed at 90% rendered as `0% - failed`, which reads as
        "never did any work". The bar should stay where the run got to; the
        failure message names the stage instead.
        """
        jobs = _RecordingJobsRepo()
        uow = _FakeUow(jobs)

        asyncio.run(
            handle_analysis_failure(
                job_id=uuid4(),
                stage="simulation",
                error_message="boom",
                uow=cast("UnitOfWork", uow),
                producer=cast("EventProducer", _FakeProducer()),
                engine_statuses={"simulation": _engine_state("failed", "boom")},
            )
        )

        _, kwargs = jobs.calls[0]
        assert (
            "progress_pct" not in kwargs
        ), "the failure path passed progress_pct, which resets the bar to 0"
        assert kwargs["progress_message"] == "Failed at stage: simulation"

    def test_pipeline_marks_the_stage_engines_failed_and_persists(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The failure map handed to the handler must already say `failed`."""
        recorder = _install_recorder(monkeypatch)
        _stub_stages(monkeypatch, recorder, boom_on="dead_code")

        captured: dict[str, object] = {}

        async def _fake_failure(**kwargs: object) -> None:
            captured.update(kwargs)

        monkeypatch.setattr(pipeline, "_handle_failure_async", _fake_failure)

        state: dict[str, object] = {"job_id": uuid4()}
        with pytest.raises(RuntimeError):
            asyncio.run(_run_pipeline(_cmd(), state))

        handed_over = cast(EngineMap, captured["engine_statuses"])
        assert handed_over["dead_code"]["status"] == "failed"
        assert "dead_code" in _text(handed_over["dead_code"]["error"])
        # Earlier stages really did finish, and must not be relabelled.
        assert handed_over["churn"]["status"] == "completed"
        # Never-reached engines keep `pending`.
        assert handed_over["simulation"]["status"] == "pending"

        # The row was written too, so a reload shows the same thing.
        assert any(
            m.get("dead_code", {}).get("status") == "failed"
            for m in recorder.engine_maps()
        )


# ======================================================================
# 3. A completed job must report every engine that ran
# ======================================================================


class _FinalizeUow:
    def __init__(self) -> None:
        self.jobs = _RecordingJobsRepo()
        self.reports = _NullRepo()
        self.score_history = _NullRepo()


class _NullRepo:
    async def save(self, *args: object, **kwargs: object) -> None:
        return None


class _NullStorage:
    async def upload(self, *args: object, **kwargs: object) -> str:
        return "reports/test.json"


class TestFinalizePreservesTheEngineMap:
    """Defect: finalize wrote `score.engine_statuses` over the pipeline's map.

    `score.engine_statuses` is the *scorer's* display view, built from
    CATEGORY_ORDER - the five scoring categories. Writing it there deleted
    dead_code, error_detection and simulation, so a fully completed job reported
    5 of its engines and the others vanished rather than showing as completed.
    A scoring view is not a record of which engines ran.
    """

    def _run(self, pipeline_map: EngineStateMap, score: Score) -> dict[str, object]:
        uow = _FinalizeUow()
        asyncio.run(
            handle_stage_finalize(
                cmd=ProcessStageCommand(job_id=uuid4(), stage="finalize"),
                uow=cast("UnitOfWork", uow),
                producer=cast("EventProducer", _FakeProducer()),
                storage=cast("AbstractStorage", _NullStorage()),
                job={"repo_id": uuid4(), "workspace_id": uuid4(), "branch": "main"},
                score=score,
                findings=[],
                languages=["Python"],
                language_breakdown=[],
                total_files=10,
                total_lines=100,
                duration_seconds=5,
                engine_statuses=pipeline_map,
            )
        )
        assert uow.jobs.calls
        return uow.jobs.calls[0][1]

    def test_all_engines_survive_finalize(self) -> None:
        pipeline_map: EngineStateMap = {
            key: _engine_state("completed") for key in ALL_ENGINES
        }
        # The scorer only knows about its five categories, and would report them
        # all as completed regardless of what the engines actually did.
        score = Score(
            overall=80,
            performance=80,
            security=80,
            reliability=80,
            maintainability=80,
            devops=80,
            engine_statuses={
                "performance": "completed",
                "security": "completed",
                "reliability": "completed",
                "maintainability": "completed",
                "devops": "completed",
            },
        )

        kwargs = self._run(pipeline_map, score)
        persisted = cast(EngineMap, kwargs["engine_statuses"])

        assert set(persisted) == set(ALL_ENGINES), (
            "finalize wrote the scorer's five-category view over the pipeline's "
            f"map; missing {sorted(set(ALL_ENGINES) - set(persisted))}"
        )
        for key in ("dead_code", "error_detection", "churn", "simulation"):
            assert persisted[key]["status"] == "completed"

    def test_a_failed_engine_is_not_overwritten_by_a_clean_score(self) -> None:
        """The whole point: the map must be the pipeline's record, not the score's."""
        pipeline_map: EngineStateMap = {
            key: _engine_state("completed") for key in ALL_ENGINES
        }
        pipeline_map["dead_code"] = _engine_state("failed", "detector blew up")
        score = Score(
            overall=None,
            blocked_by=["dead_code"],
            engine_statuses={
                "performance": "completed",
                "security": "completed",
                "reliability": "completed",
                "maintainability": "completed",
                "devops": "completed",
            },
        )

        kwargs = self._run(pipeline_map, score)
        persisted = cast(EngineMap, kwargs["engine_statuses"])

        assert persisted["dead_code"]["status"] == "failed"
        assert persisted["dead_code"]["error"] == "detector blew up"


# ======================================================================
# 4. Rows written before per-engine timings existed must still serialise
# ======================================================================


class TestLegacyEngineStatusUpgrade:
    """Defect: historical rows hold a bare status string, because that is all
    the column ever contained before per-engine timings. A strict model turns
    every one of those jobs into a 500 on read.

    The column is already JSON, so upgrading on read needs no migration.
    """

    def test_a_bare_string_still_parses(self) -> None:
        state = jobs_schemas.EngineState.model_validate("completed")

        assert state.status == "completed"
        assert state.started_at is None
        assert state.ended_at is None
        assert state.error == ""

    def test_a_whole_legacy_map_upgrades(self) -> None:
        coerced = handler_mod._coerce_engine_statuses(
            {"security": "completed", "dead_code": "failed"}
        )

        assert coerced["security"] == {
            "status": "completed",
            "started_at": None,
            "ended_at": None,
            "error": "",
        }
        assert coerced["dead_code"]["status"] == "failed"

    def test_a_modern_map_keeps_its_timings(self) -> None:
        coerced = handler_mod._coerce_engine_statuses(
            {
                "security": {
                    "status": "completed",
                    "started_at": datetime(2026, 1, 1, tzinfo=UTC),
                    "ended_at": datetime(2026, 1, 1, 0, 0, 5, tzinfo=UTC),
                    "error": "",
                }
            }
        )

        assert coerced["security"]["started_at"] == datetime(2026, 1, 1, tzinfo=UTC)
        assert coerced["security"]["ended_at"] == datetime(
            2026, 1, 1, 0, 0, 5, tzinfo=UTC
        )

    def test_an_empty_or_missing_column_coerces_to_empty(self) -> None:
        assert handler_mod._coerce_engine_statuses(None) == {}
        assert handler_mod._coerce_engine_statuses({}) == {}

    def test_round_trips_through_the_schema(self) -> None:
        coerced = handler_mod._coerce_engine_statuses({"security": "running"})

        parsed = jobs_schemas.EngineState.model_validate(coerced["security"])
        assert parsed.status == "running"


# ======================================================================
# 5. The payload shape, and what an error may say
# ======================================================================


class TestEnginePayloadShape:
    def test_every_engine_gets_all_four_fields(self) -> None:
        state: dict[str, object] = {
            "engine_statuses": {"security": "completed", "dead_code": "failed"},
            "_engine_meta": {
                "security": {"started_at": "s", "ended_at": "e"},
                "dead_code": {"started_at": "s", "ended_at": "e", "error": "why"},
            },
        }

        payload = pipeline._build_engine_payload(state)

        assert set(payload["security"]) == {"status", "started_at", "ended_at", "error"}
        assert payload["security"]["started_at"] == "s"
        assert payload["dead_code"]["error"] == "why"

    def test_an_engine_with_no_timing_yet_still_has_the_shape(self) -> None:
        payload = pipeline._build_engine_payload(
            {"engine_statuses": {"security": "running"}}
        )

        assert payload["security"]["status"] == "running"
        assert payload["security"]["started_at"] is None
        # Not `None` and not missing: the field is always present, so the
        # frontend does not have to branch on its presence.
        assert payload["security"]["error"] == ""

    def test_timestamps_are_recorded_around_an_engine(self) -> None:
        state: dict[str, object] = {}

        pipeline._mark_engine_started(state, "security")
        pipeline._mark_engine_ended(state, "security")

        payload = pipeline._build_engine_payload(
            {
                "engine_statuses": {"security": "completed"},
                "_engine_meta": state["_engine_meta"],
            }
        )
        assert payload["security"]["started_at"]
        assert payload["security"]["ended_at"]
        assert _text(payload["security"]["ended_at"]) >= _text(
            payload["security"]["started_at"]
        )


class TestEngineErrorsAreDescribedNotDumped:
    """An engine error is served to anyone who can read the job.

    A traceback carries absolute source paths and internal frames, so the
    payload gets a short description and the full traceback stays in the logs.
    """

    def test_the_description_names_the_stage_and_the_exception(self) -> None:
        described = pipeline._describe_engine_error(
            "dead_code", ValueError("bad input")
        )

        assert "dead_code" in described
        assert "ValueError" in described
        assert "bad input" in described

    def test_the_traceback_is_not_included(self) -> None:
        try:
            raise ValueError("bad input")
        except ValueError as exc:
            described = pipeline._describe_engine_error("rules", exc)

        assert "Traceback" not in described
        assert "test_engine_status_persistence.py" not in described
        assert ".py" not in described

    def test_the_description_is_bounded(self) -> None:
        described = pipeline._describe_engine_error("rules", ValueError("x" * 5000))

        assert len(described) <= 260

    def test_an_exception_with_no_message_still_describes_itself(self) -> None:
        described = pipeline._describe_engine_error("perf", ValueError())

        assert described == "perf: ValueError"


# ======================================================================
# 6. The catalogue and the pipeline must not disagree
# ======================================================================


class TestCatalogueIsTheSingleSource:
    """`dead_code`, `error_detection` and `churn` ran real work but were absent
    from three of the four lists that described engines, which is why a completed
    job reported fewer engines than it ran.
    """

    def test_every_catalogue_engine_actually_completes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`dead_code`, `error_detection` and `churn` ran real work but were
        missing from three of the four lists that described engines, so a
        completed job reported fewer engines than it ran.

        This also catches the inverse mistake: a catalogue entry that no stage
        ever drives would sit at `pending` forever.
        """
        recorder = _install_recorder(monkeypatch)
        _stub_stages(monkeypatch, recorder)

        state: dict[str, object] = {"job_id": uuid4()}
        asyncio.run(_run_pipeline(_cmd(), state))

        final = recorder.engine_maps()[-1]
        assert set(final) == set(ALL_ENGINES)
        still_pending = [k for k, v in final.items() if v["status"] != "completed"]
        assert not still_pending, f"engines never completed: {sorted(still_pending)}"

    def test_every_stage_in_the_map_is_a_stage_the_pipeline_runs(self) -> None:
        from app.core.engines import stage_to_engine_keys

        stages = set(stage_to_engine_keys())
        # If a catalogue stage is not in the pipeline's loop, its engine would sit
        # at `pending` forever.
        pipeline_stages = {
            "start",
            "clone",
            "churn",
            "parse",
            "rules",
            "save_findings",
            "dead_code",
            "errors",
            "reliability",
            "maintainability",
            "devops",
            "perf",
            "simulation",
            "score",
            "guide_gen",
            "ai_enrich",
            "finalize",
        }
        assert stages <= pipeline_stages, f"unknown stages: {stages - pipeline_stages}"

    def test_the_scored_subset_matches_the_scorer(self) -> None:
        from app.core.engines import SCORED_ENGINE_KEYS
        from app.infrastructure.scorer import ProductionReadinessScorer

        assert set(SCORED_ENGINE_KEYS) == set(ProductionReadinessScorer.CATEGORY_ORDER)

    def test_the_engine_endpoint_is_not_shadowed_by_the_job_route(self) -> None:
        """FastAPI matches in declaration order, so `/jobs/engines` declared after
        `/jobs/{job_id}` would be read as a job with id "engines".
        """
        from app.api.routers.jobs import router

        paths = [
            r.path
            for r in router.routes
            if isinstance(r, APIRoute) and r.path.startswith("/api/v1/jobs")
        ]
        assert paths.index("/api/v1/jobs/engines") < paths.index(
            "/api/v1/jobs/{job_id}"
        )
