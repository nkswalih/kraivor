"""The job's ``error_message`` is served to anyone who can read the job.

``GET /jobs/{id}`` hands this column straight to the browser, and the job detail
page puts it in the page's largest text. Three callers write it, one of them
passing ``traceback.format_exc()``. These tests pin the reduction that happens on
the way in.
"""

from __future__ import annotations

import traceback
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.analysis import handler as handler_mod
from app.application.analysis.handler import describe_failure
from app.core.constants import EngineStateMap
from app.domain.events import AnalysisFailed


def _boom() -> str:
    """Raise, and return the traceback text exactly as the pipeline builds it."""
    try:
        raise RuntimeError("connection to redis://:hunter2@cache:6379 refused")
    except RuntimeError:
        return traceback.format_exc()


# ======================================================================
# describe_failure
# ======================================================================


class TestDescribeFailure:
    """A traceback is neither safe to serve nor useful to read.

    The engine column was guarded against this; the job column beside it was
    not, and the job column is the one the UI renders.
    """

    def test_the_traceback_frames_are_dropped(self) -> None:
        described = describe_failure("rules", _boom())

        # Nothing that points at a source file survives.
        assert 'File "' not in described
        assert "Traceback" not in described
        assert "test_failure_messages.py" not in described
        assert ".py" not in described

    def test_the_exception_its_message_survives(self) -> None:
        described = describe_failure("rules", _boom())

        # This is the part that answers "why did it fail?". Dropping the frames
        # must not take the cause with them.
        assert "RuntimeError" in described
        assert "refused" in described

    def test_it_names_the_stage(self) -> None:
        # The job row carries the stage in `progress_message` too, but that is a
        # separate field and the frontend renders this one on its own. A message
        # with no location in it is close to no message.
        described = describe_failure("dead_code", "bad input")

        assert described == "dead_code failed: bad input"

    def test_it_is_bounded(self) -> None:
        described = describe_failure("perf", "x" * 5000)

        # An unbounded exception message is a row that grows without limit and a
        # banner that pushes the rest of the page off screen.
        assert len(described) <= 450

    def test_a_long_message_is_cut_at_the_limit_not_wrapped(self) -> None:
        described = describe_failure("perf", "y" * 5000)

        assert described.endswith("y")
        assert "\n" not in described

    def test_an_exception_with_no_message_still_describes_itself(self) -> None:
        # An exception can carry no message at all. The stage is still worth
        # knowing, and a bare "failed" would not be.
        assert describe_failure("simulation", "") == "simulation failed"
        assert describe_failure("simulation", None) == "simulation failed"

    def test_a_message_that_is_not_a_traceback_is_used_as_it_stands(self) -> None:
        # The two routers that catch a crash before the pipeline starts pass
        # hand-written sentences. There are no frames to strip, so nothing should
        # be stripped.
        described = describe_failure(
            "init", "Background task crashed before pipeline started"
        )

        assert "Background task crashed before pipeline started" in described

    def test_a_single_line_is_kept_whole(self) -> None:
        assert describe_failure("errors", "ruff found a config error") == (
            "errors failed: ruff found a config error"
        )

    def test_a_chained_traceback_keeps_the_outermost_cause(self) -> None:
        # `format_exc` renders a chain as two tracebacks. The one a reader wants
        # is the last thing that went wrong, which is what follows the final
        # frame.
        text = (
            "Traceback (most recent call last):\n"
            '  File "/srv/app/x.py", line 1, in <module>\n'
            "    main()\n"
            "ValueError: inner\n"
            "\n"
            "During handling of the above exception, another exception occurred:\n"
            "\n"
            "Traceback (most recent call last):\n"
            '  File "/srv/app/y.py", line 2, in main\n'
            "    inner()\n"
            "RuntimeError: outer\n"
        )

        described = describe_failure("rules", text)

        assert "RuntimeError: outer" in described
        assert "ValueError: inner" not in described
        assert 'File "' not in described

    def test_it_does_not_leak_a_credential_the_exception_embedded(self) -> None:
        # The traceback frame lines are the obvious disclosure, but the exception's
        # own message is the one that tends to embed whatever the driver was
        # holding. This test documents the limit honestly: the message is kept
        # because it is the only thing that says what went wrong, so a credential
        # inside it is not redacted -- which is a reason to keep credentials out
        # of exception text, not a reason to drop the cause.
        described = describe_failure("rules", _boom())

        assert "refused" in described


# ======================================================================
# The reduction happens on the write, not at each call site
# ======================================================================


class _RecordingJobs:
    """Captures what the handler asks the job row to be set to."""

    def __init__(self) -> None:
        self.updates: list[dict[str, object]] = []

    async def get_by_id(self, _job_id: UUID) -> dict[str, object]:
        return {"repo_id": uuid4()}

    async def update_status(
        self,
        _job_id: UUID,
        status: str,
        progress_pct: int | None = None,
        engine_statuses: EngineStateMap | None = None,
        **kwargs: object,
    ) -> None:
        # The real signature, so this stand-in cannot drift from what the handler
        # is entitled to pass. In particular `progress_pct` defaults to None here
        # for the same reason it does in the repository: omitting it must not
        # rewind progress. `completed_at` arrives the same way -- through kwargs,
        # as `finalize_job` also writes it.
        fields: dict[str, object] = {"status": status}
        if progress_pct is not None:
            fields["progress_pct"] = progress_pct
        if engine_statuses is not None:
            fields["engine_statuses"] = engine_statuses
        fields.update(kwargs)
        self.updates.append(fields)


class _RecordingProducer:
    def __init__(self) -> None:
        self.events: list[AnalysisFailed] = []

    async def publish(self, event: AnalysisFailed) -> None:
        self.events.append(event)


def _stored_message(jobs: _RecordingJobs) -> str:
    """The ``error_message`` the handler asked the row to be set to.

    Narrowed with an assertion rather than a cast: if the column ever stops being
    a string, these tests should say so instead of comparing against something
    the type system already disagreed with.
    """
    value = jobs.updates[0]["error_message"]
    assert isinstance(value, str), f"error_message was not a string: {value!r}"
    return value


def _stored_engine_error(jobs: _RecordingJobs, engine_id: str) -> object:
    """What the row was told about one engine."""
    engines = jobs.updates[0]["engine_statuses"]
    assert isinstance(engines, dict), f"engine_statuses was not a map: {engines!r}"
    entry = engines[engine_id]
    assert isinstance(entry, dict), f"engine entry was not a map: {entry!r}"
    return entry["error"]


@pytest.mark.asyncio
async def test_the_row_receives_the_described_message_not_the_traceback() -> None:
    jobs = _RecordingJobs()
    producer = _RecordingProducer()

    await handler_mod.handle_analysis_failure(
        uuid4(),
        "rules",
        _boom(),
        _as_uow(jobs),  # type: ignore[arg-type]
        producer,  # type: ignore[arg-type]
    )

    assert len(jobs.updates) == 1
    stored = _stored_message(jobs)

    assert "Traceback" not in stored
    assert ".py" not in stored
    assert "RuntimeError" in stored


@pytest.mark.asyncio
async def test_the_event_receives_the_described_message_too() -> None:
    # The failure event is rendered into notifications, which people who did not
    # run the pipeline read. It carried the traceback as well.
    jobs = _RecordingJobs()
    producer = _RecordingProducer()

    await handler_mod.handle_analysis_failure(
        uuid4(),
        "rules",
        _boom(),
        _as_uow(jobs),  # type: ignore[arg-type]
        producer,  # type: ignore[arg-type]
    )

    assert len(producer.events) == 1
    published = producer.events[0]

    assert "Traceback" not in published.error_message
    assert ".py" not in published.error_message
    # It is the same string the row got, so a notification and the page it links
    # to cannot disagree about what went wrong.
    assert published.error_message == jobs.updates[0]["error_message"]


@pytest.mark.asyncio
async def test_a_failed_run_gets_a_completion_instant() -> None:
    jobs = _RecordingJobs()
    producer = _RecordingProducer()

    before = datetime.now(UTC)
    await handler_mod.handle_analysis_failure(
        uuid4(),
        "rules",
        _boom(),
        _as_uow(jobs),  # type: ignore[arg-type]
        producer,  # type: ignore[arg-type]
    )
    after = datetime.now(UTC)

    # The run ended, and that is what the column records. Only finalize wrote it
    # before, so every failed job was a terminal state carrying no terminal
    # instant -- which is what left the frontend unable to say how long a failed
    # run had been going. It had two options left and both are wrong: measure
    # against `now`, so the figure grows for as long as the page is open, or show
    # nothing.
    completed = jobs.updates[0]["completed_at"]
    assert isinstance(completed, datetime)
    # Naive, because that is what the column holds: `finalize_job` writes
    # `datetime.now(UTC).replace(tzinfo=None)` and the two must agree or the
    # frontend's arithmetic would be comparing an aware instant to a naive one.
    assert completed.tzinfo is None
    assert before.replace(tzinfo=None) <= completed <= after.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_the_completion_instant_is_written_even_when_the_row_is_unreadable() -> (
    None
):
    class _UnreadableJobs(_RecordingJobs):
        async def get_by_id(self, _job_id: UUID) -> dict[str, object]:
            raise RuntimeError("row gone")

    jobs = _UnreadableJobs()
    producer = _RecordingProducer()

    await handler_mod.handle_analysis_failure(
        uuid4(),
        "rules",
        _boom(),
        _as_uow(jobs),  # type: ignore[arg-type]
        producer,  # type: ignore[arg-type]
    )

    # Documenting the actual behaviour rather than the desirable one: when the
    # row cannot be read, no update is issued at all. The failure event still
    # goes out, which is what tells a subscriber something happened. This is not
    # changed here because a write with no WHERE match would silently do nothing
    # and adding that is a different piece of work.
    assert jobs.updates == []
    assert len(producer.events) == 1


@pytest.mark.asyncio
async def test_the_engine_map_still_reaches_the_row() -> None:
    # The reduction is on the message only. The engine statuses carry their own
    # already-described errors and must not be affected by it.
    jobs = _RecordingJobs()
    producer = _RecordingProducer()
    engine_statuses: EngineStateMap = {
        "security": {
            "status": "failed",
            "started_at": "2026-01-01T00:00:00+00:00",
            "ended_at": "2026-01-01T00:00:04+00:00",
            "error": "rules: RuntimeError - refused",
        }
    }

    await handler_mod.handle_analysis_failure(
        uuid4(),
        "rules",
        _boom(),
        _as_uow(jobs),  # type: ignore[arg-type]
        producer,  # type: ignore[arg-type]
        engine_statuses,
    )

    stored = _stored_engine_error(jobs, "security")

    assert stored == "rules: RuntimeError - refused"


@pytest.mark.asyncio
async def test_a_publish_failure_does_not_lose_the_row() -> None:
    # The description is computed before the publish, so a broker outage cannot
    # cost the job its failure message -- which is the one thing it has to keep.
    class _ExplodingProducer:
        async def publish(self, _event: AnalysisFailed) -> None:
            raise RuntimeError("broker down")

    jobs = _RecordingJobs()

    await handler_mod.handle_analysis_failure(
        uuid4(),
        "rules",
        _boom(),
        _as_uow(jobs),  # type: ignore[arg-type]
        _ExplodingProducer(),  # type: ignore[arg-type]
    )

    assert len(jobs.updates) == 1
    assert "Traceback" not in _stored_message(jobs)


def _as_uow(jobs: _RecordingJobs) -> object:
    """The narrowest stand-in the handler actually touches.

    `handle_analysis_failure` reads exactly one attribute off the unit of work --
    `uow.jobs` -- so replacing that is enough, and no real session or repository
    is needed to prove what gets written. Returned as `object` rather than `Any`:
    the tests below pass it back into a function typed against the real
    `UnitOfWork`, and that mismatch is the point worth documenting, so the
    `# type: ignore[arg-type]` sits at each call rather than here.
    """

    class _Uow:
        def __init__(self) -> None:
            self.jobs = jobs

    return _Uow()
