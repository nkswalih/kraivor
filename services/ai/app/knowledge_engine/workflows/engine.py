"""Workflow Engine — DAG-based execution of multi-step knowledge workflows.

Supports:
- Sequential and parallel step execution
- Conditional branching
- Step output passing to downstream steps
- Retry with exponential backoff
- Timeout per step
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum

logger = logging.getLogger(__name__)


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


class WorkflowStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


@dataclass
class StepResult:
    """Result from a single workflow step."""
    step_id: str
    status: StepStatus
    output: dict = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0
    started_at: float | None = None
    completed_at: float | None = None


@dataclass
class WorkflowResult:
    """Result from a complete workflow execution."""
    workflow_id: str
    workflow_name: str
    status: WorkflowStatus
    step_results: dict[str, StepResult] = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    total_duration_ms: float = 0.0
    started_at: float | None = None
    completed_at: float | None = None
    error: str | None = None


class WorkflowStep:
    """A single step in a workflow."""

    def __init__(
        self,
        step_id: str,
        name: str,
        handler: callable,
        depends_on: list[str] | None = None,
        timeout_seconds: int = 300,
        retry_count: int = 2,
        condition: callable | None = None,
    ):
        self.step_id = step_id
        self.name = name
        self.handler = handler
        self.depends_on = depends_on or []
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count
        self.condition = condition


async def _run_single_step(
    step: WorkflowStep,
    context: dict,
    workspace_id: str | None,
) -> StepResult:
    """Execute a single step with timeout."""
    step_result = StepResult(
        step_id=step.step_id,
        status=StepStatus.RUNNING,
        started_at=time.time(),
    )
    try:
        output = await asyncio.wait_for(
            step.handler(context, workspace_id),
            timeout=step.timeout_seconds,
        )
        step_result.status = StepStatus.COMPLETED
        step_result.output = output or {}
    except TimeoutError:
        step_result.status = StepStatus.TIMED_OUT
        step_result.error = f"Step timed out after {step.timeout_seconds}s"
    except Exception as e:
        step_result.status = StepStatus.FAILED
        step_result.error = str(e)
        logger.error("Step %s failed: %s", step.step_id, e)

    step_result.completed_at = time.time()
    step_result.duration_ms = (step_result.completed_at - step_result.started_at) * 1000
    return step_result


async def _run_step_with_retry(
    step: WorkflowStep,
    context: dict,
    workspace_id: str | None,
) -> StepResult:
    """Execute a step with retry and exponential backoff."""
    last_result = None
    for attempt in range(step.retry_count + 1):
        last_result = await _run_single_step(step, context, workspace_id)
        if last_result.status == StepStatus.COMPLETED:
            return last_result
        if attempt < step.retry_count:
            await asyncio.sleep(2 ** attempt)
    return last_result


class WorkflowEngine:
    """Executes DAG-based knowledge workflows."""

    def __init__(self):
        self._running_workflows: dict[str, WorkflowResult] = {}

    async def execute(
        self,
        workflow_id: str,
        workflow_name: str,
        steps: list[WorkflowStep],
        initial_inputs: dict | None = None,
        workspace_id: str | None = None,
    ) -> WorkflowResult:
        """Execute a workflow DAG."""
        result = WorkflowResult(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            status=WorkflowStatus.RUNNING,
            started_at=time.time(),
        )
        self._running_workflows[workflow_id] = result

        # Build adjacency and in-degree maps
        in_degree = {s.step_id: len(s.depends_on) for s in steps}
        dependents: dict[str, list[str]] = {s.step_id: [] for s in steps}
        for s in steps:
            for dep in s.depends_on:
                dependents[dep].append(s.step_id)

        # Collect outputs from all steps
        all_outputs: dict[str, dict] = initial_inputs or {}
        completed_steps: set[str] = set()
        failed_steps: set[str] = set()

        while len(completed_steps) + len(failed_steps) < len(steps):
            # Find steps ready to run
            ready = []
            for s in steps:
                if s.step_id in completed_steps or s.step_id in failed_steps:
                    continue
                if in_degree[s.step_id] > 0:
                    continue
                # Check condition
                if s.condition and not s.condition(all_outputs):
                    result.step_results[s.step_id] = StepResult(
                        step_id=s.step_id,
                        status=StepStatus.SKIPPED,
                    )
                    completed_steps.add(s.step_id)
                    continue
                ready.append(s)

            if not ready and len(completed_steps) + len(failed_steps) < len(steps):
                result.status = WorkflowStatus.FAILED
                result.error = "Workflow deadlocked: unmet dependencies"
                break

            # Execute ready steps in parallel
            tasks = [
                _run_step_with_retry(s, all_outputs, workspace_id)
                for s in ready
            ]
            step_results = await asyncio.gather(*tasks)

            for sr in step_results:
                result.step_results[sr.step_id] = sr
                if sr.status == StepStatus.COMPLETED:
                    completed_steps.add(sr.step_id)
                    all_outputs[sr.step_id] = sr.output
                    for dep_id in dependents.get(sr.step_id, []):
                        in_degree[dep_id] -= 1
                else:
                    failed_steps.add(sr.step_id)
                    for dep_id in dependents.get(sr.step_id, []):
                        in_degree[dep_id] = 0

        # Determine final status
        result.completed_at = time.time()
        result.total_duration_ms = (result.completed_at - result.started_at) * 1000
        result.outputs = all_outputs

        if len(completed_steps) == len(steps):
            result.status = WorkflowStatus.COMPLETED
        elif failed_steps:
            result.status = (
                WorkflowStatus.PARTIALLY_COMPLETED
                if completed_steps
                else WorkflowStatus.FAILED
            )

        del self._running_workflows[workflow_id]
        return result

    async def get_status(self, workflow_id: str) -> WorkflowResult | None:
        """Get the current status of a running workflow."""
        return self._running_workflows.get(workflow_id)

    def list_running(self) -> list[str]:
        """List IDs of currently running workflows."""
        return list(self._running_workflows.keys())
