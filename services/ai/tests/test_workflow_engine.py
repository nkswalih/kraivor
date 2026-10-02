"""Tests for the workflow DAG engine.

``knowledge_engine/workflows/engine.py`` had no tests at all -- 129 statements
at 0.00% coverage, despite being the thing that actually executes every
multi-step knowledge workflow. It is pure orchestration logic with no
database or network dependency, so these tests drive the real engine with
real handlers rather than stubbing the code under test.

Two behaviours here are surprising enough to be worth pinning explicitly:

* A failed step does **not** block its dependents. ``execute`` forces the
  dependent's in-degree to 0 when an upstream step fails, so the dependent
  still runs and the workflow ends PARTIALLY_COMPLETED rather than stopping.
* A skipped step (condition returned false) is counted as completed for the
  purposes of the final COMPLETED check.

Only the retry backoff sleep is faked, to keep the suite fast; the ordering,
status and output-passing assertions all run against the real engine.
"""

import asyncio

import pytest

from app.knowledge_engine.workflows.engine import (
    StepStatus,
    WorkflowEngine,
    WorkflowStatus,
    WorkflowStep,
    _run_single_step,
    _run_step_with_retry,
)


@pytest.fixture
def no_backoff_sleep(monkeypatch):
    """Record retry backoff delays instead of really sleeping 1s, 2s, 4s..."""
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return delays


def make_recorder(result=None, raises=None):
    """A handler that appends its calls to a list and returns `result`."""

    calls = []

    async def handler(context, workspace_id):
        calls.append((dict(context), workspace_id))
        if raises is not None:
            raise raises
        return result

    handler.calls = calls
    return handler


# ── _run_single_step ────────────────────────────────────────────────────────


class TestRunSingleStep:
    async def test_success_records_completed_and_output(self):
        step = WorkflowStep("s1", "Step One", make_recorder({"value": 42}))

        result = await _run_single_step(step, {"ctx": True}, "ws-1")

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"value": 42}
        assert result.error is None

    async def test_passes_context_and_workspace_to_handler(self):
        handler = make_recorder({"ok": True})
        step = WorkflowStep("s1", "Step One", handler)

        await _run_single_step(step, {"topic": "kraivor"}, "ws-7")

        assert handler.calls == [({"topic": "kraivor"}, "ws-7")]

    async def test_none_output_becomes_empty_dict(self):
        # The engine stores `output or {}`, so a handler that returns None
        # yields a dict, not None -- downstream steps index into it blindly.
        step = WorkflowStep("s1", "Step One", make_recorder(result=None))

        result = await _run_single_step(step, {}, None)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {}

    async def test_handler_exception_becomes_failed_with_message(self):
        step = WorkflowStep("s1", "Step One", make_recorder(raises=ValueError("boom")))

        result = await _run_single_step(step, {}, None)

        assert result.status == StepStatus.FAILED
        assert result.error == "boom"

    async def test_timeout_becomes_timed_out_with_limit_in_message(self):
        async def slow(context, workspace_id):
            await asyncio.sleep(5)
            return {}

        step = WorkflowStep("s1", "Slow", slow, timeout_seconds=0.05)

        result = await _run_single_step(step, {}, None)

        assert result.status == StepStatus.TIMED_OUT
        assert "0.05s" in result.error

    async def test_records_timing_on_success(self):
        step = WorkflowStep("s1", "Step One", make_recorder({"v": 1}))

        result = await _run_single_step(step, {}, None)

        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.completed_at >= result.started_at
        assert result.duration_ms >= 0


# ── _run_step_with_retry ─────────────────────────────────────────────────────


class TestRunStepWithRetry:
    async def test_success_on_first_attempt_runs_once(self, no_backoff_sleep):
        handler = make_recorder({"ok": True})
        step = WorkflowStep("s1", "Step One", handler, retry_count=2)

        result = await _run_step_with_retry(step, {}, None)

        assert result.status == StepStatus.COMPLETED
        assert len(handler.calls) == 1
        assert no_backoff_sleep == []

    async def test_retries_after_failure_then_succeeds(self, no_backoff_sleep):
        attempts = []

        async def flaky(context, workspace_id):
            attempts.append(1)
            if len(attempts) < 3:
                raise RuntimeError("transient")
            return {"recovered": True}

        step = WorkflowStep("s1", "Flaky", flaky, retry_count=2)

        result = await _run_step_with_retry(step, {}, None)

        assert result.status == StepStatus.COMPLETED
        assert result.output == {"recovered": True}
        assert len(attempts) == 3
        # Exponential backoff between attempts, starting at 2**0 == 1s.
        assert no_backoff_sleep == [1, 2]

    async def test_gives_up_after_retry_count_attempts(self, no_backoff_sleep):
        handler = make_recorder(raises=RuntimeError("always"))
        step = WorkflowStep("s1", "Doomed", handler, retry_count=2)

        result = await _run_step_with_retry(step, {}, None)

        assert result.status == StepStatus.FAILED
        assert result.error == "always"
        # retry_count=2 means 1 initial attempt plus 2 retries.
        assert len(handler.calls) == 3
        assert no_backoff_sleep == [1, 2]

    async def test_retry_count_zero_never_retries(self, no_backoff_sleep):
        handler = make_recorder(raises=RuntimeError("nope"))
        step = WorkflowStep("s1", "Once", handler, retry_count=0)

        result = await _run_step_with_retry(step, {}, None)

        assert result.status == StepStatus.FAILED
        assert len(handler.calls) == 1
        assert no_backoff_sleep == []


# ── WorkflowStep defaults ───────────────────────────────────────────────────


class TestWorkflowStepDefaults:
    def test_optional_fields_get_defaults(self):
        async def handler(context, workspace_id):
            return {}

        step = WorkflowStep("s1", "Step One", handler)

        assert step.depends_on == []
        assert step.timeout_seconds == 300
        assert step.retry_count == 2
        assert step.condition is None


# ── WorkflowEngine.execute ──────────────────────────────────────────────────


class TestExecute:
    async def test_empty_workflow_completes(self):
        result = await WorkflowEngine().execute("wf", "Empty", [])

        assert result.status == WorkflowStatus.COMPLETED
        assert result.step_results == {}

    async def test_single_step_output_lands_in_workflow_outputs(self):
        step = WorkflowStep("only", "Only", make_recorder({"total": 7}))

        result = await WorkflowEngine().execute("wf", "Single", [step])

        assert result.status == WorkflowStatus.COMPLETED
        assert result.outputs["only"] == {"total": 7}
        assert result.step_results["only"].status == StepStatus.COMPLETED

    async def test_initial_inputs_are_preserved_and_extended(self):
        step = WorkflowStep("s", "S", make_recorder({"new": 1}))

        result = await WorkflowEngine().execute(
            "wf", "W", [step], initial_inputs={"seeded": "yes"}
        )

        assert result.outputs["seeded"] == "yes"
        assert result.outputs["s"] == {"new": 1}

    async def test_sequential_chain_runs_in_dependency_order(self):
        order = []

        def record(name):
            async def handler(context, workspace_id):
                order.append(name)
                return {"from": name}

            return handler

        steps = [
            WorkflowStep("first", "First", record("first")),
            WorkflowStep("second", "Second", record("second"), depends_on=["first"]),
            WorkflowStep("third", "Third", record("third"), depends_on=["second"]),
        ]

        result = await WorkflowEngine().execute("wf", "Chain", steps)

        assert order == ["first", "second", "third"]
        assert result.status == WorkflowStatus.COMPLETED

    async def test_downstream_step_receives_upstream_output_in_context(self):
        seen = {}

        async def upstream(context, workspace_id):
            return {"documents": 3}

        async def downstream(context, workspace_id):
            seen.update(context)
            return {}

        steps = [
            WorkflowStep("up", "Up", upstream),
            WorkflowStep("down", "Down", downstream, depends_on=["up"]),
        ]

        await WorkflowEngine().execute("wf", "Pass", steps)

        assert seen["up"] == {"documents": 3}

    async def test_independent_steps_all_run(self):
        a = make_recorder({"a": 1})
        b = make_recorder({"b": 2})
        steps = [WorkflowStep("a", "A", a), WorkflowStep("b", "B", b)]

        result = await WorkflowEngine().execute("wf", "Parallel", steps)

        assert result.status == WorkflowStatus.COMPLETED
        assert len(a.calls) == 1
        assert len(b.calls) == 1
        assert set(result.outputs) == {"a", "b"}

    async def test_workspace_id_is_threaded_to_handlers(self):
        handler = make_recorder({})
        step = WorkflowStep("s", "S", handler)

        await WorkflowEngine().execute("wf", "W", [step], workspace_id="ws-99")

        assert handler.calls[0][1] == "ws-99"

    async def test_failing_step_yields_failed_workflow(self):
        step = WorkflowStep("s", "S", make_recorder(raises=RuntimeError("nope")))

        result = await WorkflowEngine().execute("wf", "Fail", [step])

        assert result.status == WorkflowStatus.FAILED
        assert result.step_results["s"].status == StepStatus.FAILED

    async def test_failure_upstream_does_not_block_its_dependent(self):
        # execute() zeroes a dependent's in-degree when its dependency fails,
        # so the dependent still runs and the workflow is PARTIALLY_COMPLETED.
        async def broken(context, workspace_id):
            raise RuntimeError("upstream down")

        dependent = make_recorder({"recovered": True})
        steps = [
            WorkflowStep("up", "Up", broken),
            WorkflowStep("down", "Down", dependent, depends_on=["up"]),
        ]

        result = await WorkflowEngine().execute("wf", "Partial", steps)

        assert result.status == WorkflowStatus.PARTIALLY_COMPLETED
        assert result.step_results["up"].status == StepStatus.FAILED
        assert result.step_results["down"].status == StepStatus.COMPLETED
        assert len(dependent.calls) == 1

    async def test_dependency_cycle_is_reported_as_deadlock(self):
        async def handler(context, workspace_id):
            return {}

        steps = [
            WorkflowStep("a", "A", handler, depends_on=["b"]),
            WorkflowStep("b", "B", handler, depends_on=["a"]),
        ]

        result = await WorkflowEngine().execute("wf", "Cycle", steps)

        assert result.status == WorkflowStatus.FAILED
        assert "deadlock" in result.error
        assert result.error == "Workflow deadlocked: unmet dependencies"

    async def test_false_condition_skips_step_and_still_completes(self):
        ran = []

        async def never(context, workspace_id):
            ran.append(1)
            return {}

        step = WorkflowStep("s", "S", never, condition=lambda ctx: False)

        result = await WorkflowEngine().execute("wf", "Cond", [step])

        assert result.step_results["s"].status == StepStatus.SKIPPED
        assert ran == []
        # A skipped step counts as completed for the final status.
        assert result.status == WorkflowStatus.COMPLETED

    async def test_true_condition_runs_step(self):
        async def handler(context, workspace_id):
            return {"ran": True}

        step = WorkflowStep("s", "S", handler, condition=lambda ctx: True)

        result = await WorkflowEngine().execute("wf", "Cond", [step])

        assert result.step_results["s"].status == StepStatus.COMPLETED
        assert result.status == WorkflowStatus.COMPLETED

    async def test_condition_sees_accumulated_outputs(self):
        seen = {}

        async def producer(context, workspace_id):
            return {"flag": "on"}

        def condition(ctx):
            seen.update(ctx)
            return ctx.get("producer", {}).get("flag") == "on"

        async def gated(context, workspace_id):
            return {}

        steps = [
            WorkflowStep("producer", "P", producer),
            WorkflowStep("gated", "G", gated, depends_on=["producer"], condition=condition),
        ]

        result = await WorkflowEngine().execute("wf", "Gate", steps)

        assert seen.get("producer") == {"flag": "on"}
        assert result.step_results["gated"].status == StepStatus.COMPLETED

    async def test_result_carries_timing_and_identity(self):
        step = WorkflowStep("s", "S", make_recorder({}))

        result = await WorkflowEngine().execute("wf-1", "Named", [step])

        assert result.workflow_id == "wf-1"
        assert result.workflow_name == "Named"
        assert result.started_at is not None
        assert result.completed_at >= result.started_at
        assert result.total_duration_ms >= 0


# ── running-workflow bookkeeping ────────────────────────────────────────────


class TestRunningWorkflowTracking:
    async def test_get_status_returns_live_result_while_running(self):
        engine = WorkflowEngine()
        observed = {}

        async def inspecting(context, workspace_id):
            # Snapshot the fields inside the handler. get_status hands back the
            # live WorkflowResult, so a reference kept past this point has
            # already advanced to COMPLETED by the time it is asserted on.
            live = await engine.get_status("wf-live")
            observed["workflow_id"] = live.workflow_id
            observed["status"] = live.status
            return {}

        await engine.execute("wf-live", "Live", [WorkflowStep("s", "S", inspecting)])

        assert observed["workflow_id"] == "wf-live"
        assert observed["status"] == WorkflowStatus.RUNNING

    async def test_get_status_hands_back_the_live_result_not_a_snapshot(self):
        # execute() mutates one WorkflowResult in place and get_status returns
        # that same object, so anything holding the reference sees the final
        # state rather than the state at fetch time. Pinned so nobody later
        # assumes it is an immutable copy.
        engine = WorkflowEngine()
        captured = []

        async def inspecting(context, workspace_id):
            captured.append(await engine.get_status("wf-alias"))
            return {}

        result = await engine.execute(
            "wf-alias", "Alias", [WorkflowStep("s", "S", inspecting)]
        )

        assert captured[0] is result
        assert captured[0].status == WorkflowStatus.COMPLETED

    async def test_workflow_is_removed_from_tracking_once_finished(self):
        engine = WorkflowEngine()
        await engine.execute("wf-done", "Done", [WorkflowStep("s", "S", make_recorder({}))])

        assert await engine.get_status("wf-done") is None
        assert engine.list_running() == []

    async def test_unknown_workflow_status_is_none(self):
        assert await WorkflowEngine().get_status("never-existed") is None

    async def test_workflow_is_listed_while_running_then_cleared(self):
        engine = WorkflowEngine()
        started = asyncio.Event()
        release = asyncio.Event()

        async def blocking(context, workspace_id):
            started.set()
            await release.wait()
            return {}

        task = asyncio.create_task(
            engine.execute("wf-a", "A", [WorkflowStep("s", "S", blocking)])
        )
        # Wait for the handler to actually be running rather than sampling on a
        # timer, so this cannot race.
        await started.wait()

        assert engine.list_running() == ["wf-a"]
        live = await engine.get_status("wf-a")
        assert live is not None
        assert live.status == WorkflowStatus.RUNNING

        release.set()
        completed = await task

        # Assert on the returned result instead of discarding it. Deregistration
        # only proves execute() returned, not that the run succeeded -- a
        # FAILED result deregisters just the same and used to satisfy this test.
        assert completed.status == WorkflowStatus.COMPLETED

        assert engine.list_running() == []
        assert await engine.get_status("wf-a") is None