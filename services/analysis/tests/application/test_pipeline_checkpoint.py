"""Resuming a failed run: the saved position, and where it points.

The contract these tests pin: a run that dies at stage N leaves a file saying
stage N-1 finished, a retry starts at stage N, and nothing before N runs again
-- those stages' rows are still in the database, and a second copy of them
would not be an improvement.

The position file itself is the whole mechanism, so the first group treats it
as the load-bearing artifact it is: torn, foreign, or absent content must read
as "no position" rather than as a position, because the failure mode of a
misread checkpoint is a pipeline starting at the wrong stage.
"""

import asyncio
import pickle
from uuid import UUID, uuid4

import pytest

from app.application.analysis.commands import StartAnalysisCommand
from app.application.tasks import checkpoint, pipeline
from app.application.tasks.checkpoint import (
    delete_checkpoint,
    load_checkpoint,
    save_checkpoint,
)

_STAGE_NAMES = (
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
)


class _QuietProducer:
    """Stands in for the event producer: nothing is running a broker here."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    async def publish(self, event: object) -> None:
        return None


async def _quiet_persist(state: dict[str, object]) -> None:
    """Stands in for the engine-status write: a DB round-trip this suite's
    checkpoint tests have no stake in. Its own behaviour belongs to
    `test_engine_status_persistence.py`."""
    return None


def _cmd() -> StartAnalysisCommand:
    return StartAnalysisCommand(
        repo_id=uuid4(),
        workspace_id=uuid4(),
        triggered_by=uuid4(),
        trigger_type="manual",
        repo_url="https://github.com/example/repo",
    )


def _stub_stages(
    monkeypatch: pytest.MonkeyPatch,
    observe_job_id: UUID | None = None,
) -> list[str]:
    """Replace every stage with a recorder; return the executed-name list.

    When `observe_job_id` is given, each stub also notes what the position
    file said at the moment that stage *started* -- which is how "saved after
    every completed stage" is checked from outside the loop.
    """
    executed: list[str] = []

    def _make(name: str) -> object:
        async def _stage(state: dict[str, object], *args: object) -> None:
            if observe_job_id is not None:
                saved = load_checkpoint(observe_job_id)
                executed.append(
                    f"sees:{saved.get('_last_stage') if saved else None}"
                )
            executed.append(name)

        return _stage

    for name in _STAGE_NAMES:
        monkeypatch.setattr(pipeline, f"_stage_{name}", _make(name))
    monkeypatch.setattr(pipeline, "EventProducer", _QuietProducer)
    monkeypatch.setattr(pipeline, "_persist_engine_statuses", _quiet_persist)
    return executed


# ======================================================================
# The position file
# ======================================================================


class TestThePositionFile:
    def test_roundtrip_preserves_position_and_state(self) -> None:
        job_id = uuid4()
        state: dict[str, object] = {
            "_last_stage": "dead_code",
            "repo_path": "/tmp/analysis/abc",
            "languages": ["python", "go"],
        }

        save_checkpoint(job_id, state)
        restored = load_checkpoint(job_id)

        assert restored is not None
        assert restored["_last_stage"] == "dead_code"
        assert restored["repo_path"] == "/tmp/analysis/abc"
        assert restored["languages"] == ["python", "go"]

    def test_the_monotonic_clock_marker_never_crosses_processes(self) -> None:
        # A `time.monotonic()` value counts seconds since this machine's last
        # boot, recorded from one process's point of contact with that clock.
        # A resumed run rebuilds the marker on entry, so the saved one is
        # stale data waiting to be trusted -- and trusting it would make
        # every resumed duration nonsense.
        job_id = uuid4()
        save_checkpoint(job_id, {"_last_stage": "parse", "_pipeline_start": 1234.5})

        restored = load_checkpoint(job_id)

        assert restored is not None
        assert "_pipeline_start" not in restored

    def test_no_file_reads_as_no_position(self) -> None:
        assert load_checkpoint(uuid4()) is None

    def test_a_torn_write_reads_as_no_position(self) -> None:
        # What a reader can actually encounter when a save is cut short is a
        # truncated pickle -- the file is written to a temp name and renamed
        # into place, so a half-written *main* file is the one shape that
        # cannot occur. The safe reading of a torn one is "nothing here",
        # never "half a position".
        job_id = uuid4()
        save_checkpoint(job_id, {"_last_stage": "parse"})
        checkpoint._checkpoint_path(job_id).write_bytes(b"\x80\x05}q\x00X\x0a\x00\x00")

        assert load_checkpoint(job_id) is None

    def test_foreign_content_reads_as_no_position(self) -> None:
        # A file in the right place that did not come from a pipeline run.
        # Pickle yields whatever it holds; the isinstance guard is what makes
        # "a list" answer the same as "nothing at all".
        job_id = uuid4()
        path = checkpoint._checkpoint_path(job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pickle.dumps(["not", "a", "state"]))

        assert load_checkpoint(job_id) is None

    def test_a_failed_save_leaves_neither_torn_file_nor_temp(self) -> None:
        job_id = uuid4()
        with pytest.raises(pickle.PicklingError):
            save_checkpoint(job_id, {"_last_stage": "parse", "bad": lambda: None})

        # Nothing was renamed into place, and the temp file was unlinked --
        # the next reader sees an absent position, not a half-written one.
        assert load_checkpoint(job_id) is None
        assert list(checkpoint._checkpoint_dir().iterdir()) == []

    def test_delete_removes_it_and_tolerates_absence(self) -> None:
        job_id = uuid4()
        save_checkpoint(job_id, {"_last_stage": "clone"})
        delete_checkpoint(job_id)
        assert load_checkpoint(job_id) is None
        delete_checkpoint(job_id)  # a second delete must not raise


# ======================================================================
# The stage inventory
# ======================================================================


class TestTheStageInventory:
    def test_progress_table_status_table_and_loop_describe_one_pipeline(
        self,
    ) -> None:
        """`plan_resume` reads positions from `_STAGE_PROGRESS`, and the loop
        runs `_stages`. If the two orders ever drift -- a stage added to one
        and not the other -- resume would aim at a stage the loop slices
        differently from the table it trusted. Pinned together, an edit to one
        fails here instead of resuming at the wrong place in production.
        """
        names = [name for name, _, _ in pipeline._stages(_cmd())]
        assert names == list(pipeline._STAGE_PROGRESS)
        assert names == list(pipeline._STAGE_STATUS)
        assert names == list(_STAGE_NAMES)


# ======================================================================
# Saving after every stage
# ======================================================================


class TestTheLoopSavesPositions:
    def test_each_stage_starts_with_the_previous_ones_position_on_disk(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job_id = uuid4()
        executed = _stub_stages(monkeypatch, observe_job_id=job_id)

        asyncio.run(pipeline._run_pipeline(_cmd(), {"job_id": job_id}))

        # At the first stage nothing has finished, so no file exists. From
        # clone onward each stage reads the position of the stage before it,
        # which is only possible if the save happened on the previous stage's
        # success path -- while its truth was still current.
        assert executed[0] == "sees:None"
        seen = [
            None if entry == "sees:None" else entry.split("sees:")[1]
            for entry in executed
            if entry.startswith("sees:")
        ]
        assert seen == [None, *_STAGE_NAMES[:-1]]

        final = load_checkpoint(job_id)
        assert final is not None
        assert final["_last_stage"] == "finalize"

    def test_a_stage_that_raises_leaves_the_last_completed_position(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The failing stage never reaches the save, so the file on disk names
        # the stage before it -- precisely the stage a retry must resume
        # after. `_stub_stages` stands up the producers and persistence; this
        # one additionally needs a failure path that does not reach for a
        # database the assertion is not about.
        job_id = uuid4()

        def _make(name: str) -> object:
            async def _stage(state: dict[str, object], *args: object) -> None:
                if name == "dead_code":
                    raise RuntimeError("dead_code exploded")

            return _stage

        for name in _STAGE_NAMES:
            monkeypatch.setattr(pipeline, f"_stage_{name}", _make(name))
        monkeypatch.setattr(pipeline, "EventProducer", _QuietProducer)
        monkeypatch.setattr(pipeline, "_persist_engine_statuses", _quiet_persist)

        async def _quiet_failure(**kwargs: object) -> None:
            return None

        monkeypatch.setattr(pipeline, "_handle_failure_async", _quiet_failure)

        with pytest.raises(RuntimeError):
            asyncio.run(pipeline._run_pipeline(_cmd(), {"job_id": job_id}))

        saved = load_checkpoint(job_id)
        assert saved is not None
        assert saved["_last_stage"] == "save_findings"


# ======================================================================
# Where a retry would start
# ======================================================================


class TestResumePlanning:
    @pytest.mark.parametrize(
        ("last", "expected"),
        [
            ("start", "clone"),
            ("parse", "rules"),
            ("dead_code", "errors"),
            ("ai_enrich", "finalize"),
        ],
    )
    def test_points_at_the_stage_that_failed(self, last: str, expected: str) -> None:
        assert pipeline._plan_from_state({"_last_stage": last}) == expected

    def test_after_finalize_there_is_nothing_left_to_resume_to(self) -> None:
        # Re-running earlier stages against rows they already wrote is the
        # duplicate-findings bug this whole mechanism exists to avoid.
        assert pipeline._plan_from_state({"_last_stage": "finalize"}) is None

    @pytest.mark.parametrize("state", [{}, {"_last_stage": 42}, {"_last_stage": "?"}])
    def test_an_unreadable_position_refuses_rather_than_guessing(
        self, state: dict[str, object]
    ) -> None:
        assert pipeline._plan_from_state(state) is None

    def test_plan_resume_reads_the_saved_file(self) -> None:
        job_id = uuid4()
        save_checkpoint(job_id, {"_last_stage": "errors"})
        assert pipeline.plan_resume(job_id) == "reliability"

    def test_plan_resume_without_a_file_is_none(self) -> None:
        assert pipeline.plan_resume(uuid4()) is None

    def test_deep_churn_without_its_workspace_refuses(self, tmp_path) -> None:
        # Churn alone reads git history off the disk. A container recreated
        # since the failure took /tmp with it, so a depth-2 run handed that
        # path would fail *again* at churn -- an honest refusal that sends the
        # client to a fresh analysis is the better answer.
        state = {"_last_stage": "clone", "repo_path": str(tmp_path / "gone")}
        assert pipeline._plan_from_state(state, depth=2) is None

    def test_deep_churn_with_its_workspace_resumes(self, tmp_path) -> None:
        state = {"_last_stage": "clone", "repo_path": str(tmp_path)}
        assert pipeline._plan_from_state(state, depth=2) == "churn"

    def test_a_shallow_clone_never_touches_the_disk(self, tmp_path) -> None:
        # depth <= 1 skips churn outright inside the stage itself, so the
        # workspace's existence is not a question worth asking.
        state = {"_last_stage": "clone", "repo_path": str(tmp_path / "gone")}
        assert pipeline._plan_from_state(state, depth=1) == "churn"


# ======================================================================
# Resuming the loop
# ======================================================================


class TestResumeSlicesTheLoop:
    def test_stages_before_the_resume_point_never_run(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        executed = _stub_stages(monkeypatch)
        state: dict[str, object] = {"job_id": uuid4()}

        asyncio.run(pipeline._run_pipeline(_cmd(), state, resume_from="rules"))

        assert executed == list(_STAGE_NAMES[_STAGE_NAMES.index("rules") :])

    def test_the_checkpointed_engine_map_survives_the_resume(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The loop begins by giving a fresh run its all-pending map. On a
        # fresh run that is correct; on a resumed one a *replacement* would
        # erase every engine the previous attempt finished, and the score
        # reads that map -- hence `setdefault` and this test.
        _stub_stages(monkeypatch)
        state: dict[str, object] = {
            "job_id": uuid4(),
            "engine_statuses": {"perf": "completed", "dead_code": "completed"},
            "_engine_meta": {"perf": {"ended_at": "2026-01-01T00:00:00+00:00"}},
        }

        asyncio.run(pipeline._run_pipeline(_cmd(), state, resume_from="finalize"))

        statuses = state["engine_statuses"]
        assert statuses["perf"] == "completed"  # type: ignore[index]
        assert statuses["dead_code"] == "completed"  # type: ignore[index]
        # The timings came through too -- history, not something to blank.
        meta = state["_engine_meta"]
        assert meta["perf"]["ended_at"] == "2026-01-01T00:00:00+00:00"  # type: ignore[index]

    def test_an_unknown_resume_point_is_refused_before_any_stage_runs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        executed = _stub_stages(monkeypatch)

        with pytest.raises(ValueError, match="unknown stage"):
            asyncio.run(
                pipeline._run_pipeline(
                    _cmd(), {"job_id": uuid4()}, resume_from="teleport"
                )
            )

        assert executed == []


# ======================================================================
# run_full_analysis: the entry point the retry endpoint calls
# ======================================================================


class TestRunFullAnalysisResume:
    @staticmethod
    def _cmd_dict(job_id: object, resume: bool = True) -> dict[str, object]:
        cmd: dict[str, object] = {
            "repo_id": str(uuid4()),
            "workspace_id": str(uuid4()),
            "triggered_by": str(uuid4()),
            "trigger_type": "manual",
            "repo_url": "https://github.com/example/repo",
            "job_id": str(job_id),
        }
        if resume:
            cmd["resume"] = True
        return cmd

    def test_resume_without_a_saved_position_fails_without_running(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The endpoint checks before it claims, so reaching this means a race
        # -- the file vanished between check and start. Running anyway would
        # begin at stage one and duplicate everything the attempt already
        # wrote, so the honest outcome is a job that says why it cannot
        # continue rather than a pipeline that pretends to be fresh.
        ran: list[str] = []
        failures: list[tuple[str, str]] = []

        async def _fake_pipeline(
            cmd: object, state: object, *, resume_from: str | None = None
        ) -> None:
            ran.append(resume_from or "full")

        async def _fake_failure(**kwargs: object) -> None:
            failures.append(
                (str(kwargs.get("stage")), str(kwargs.get("error_message")))
            )

        monkeypatch.setattr(pipeline, "_run_pipeline", _fake_pipeline)
        monkeypatch.setattr(pipeline, "_handle_failure_async", _fake_failure)

        job_id = uuid4()
        result = asyncio.run(pipeline.run_full_analysis(self._cmd_dict(job_id)))

        assert result["status"] == "failed"
        assert ran == []
        assert failures[0][0] == "resume"
        assert "cannot resume" in failures[0][1]

    def test_resume_continues_at_the_saved_stage_and_cleans_up_on_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job_id = uuid4()
        save_checkpoint(job_id, {"_last_stage": "parse", "languages": ["python"]})
        seen: dict[str, object] = {}

        async def _fake_pipeline(
            cmd: object, state: dict[str, object], *, resume_from: str | None = None
        ) -> None:
            seen["resume_from"] = resume_from
            seen["languages"] = state.get("languages")
            seen["job_id_kept"] = state.get("job_id")

        monkeypatch.setattr(pipeline, "_run_pipeline", _fake_pipeline)

        result = asyncio.run(pipeline.run_full_analysis(self._cmd_dict(job_id)))

        assert seen["resume_from"] == "rules"
        assert seen["languages"] == ["python"]
        assert seen["job_id_kept"] == job_id
        assert result["status"] == "completed"
        # A finished run has nothing left to resume from; the file goes.
        assert load_checkpoint(job_id) is None

    def test_a_plain_run_still_starts_at_the_beginning(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, object] = {}

        async def _fake_pipeline(
            cmd: object, state: object, *, resume_from: str | None = None
        ) -> None:
            seen["resume_from"] = resume_from

        monkeypatch.setattr(pipeline, "_run_pipeline", _fake_pipeline)

        asyncio.run(pipeline.run_full_analysis(self._cmd_dict(uuid4(), resume=False)))

        assert seen["resume_from"] is None
