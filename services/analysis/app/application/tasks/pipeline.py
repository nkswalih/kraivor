"""Full analysis pipeline orchestrator.

Runs all stages sequentially, sharing an in-memory state dict.
Each stage is wrapped with error handling — on failure the job is
marked as failed immediately and the pipeline halts.
"""

import asyncio
import time
import traceback
from datetime import datetime
from typing import cast
from uuid import UUID

from app.application.analysis.commands import (
    ProcessStageCommand,
    StartAnalysisCommand,
)
from app.application.analysis.handler import (
    _push_progress,
    handle_analysis_failure,
    handle_save_analysis_metadata,
    handle_save_findings,
    handle_stage_ai_enrich,
    handle_stage_churn,
    handle_stage_clone,
    handle_stage_dead_code,
    handle_stage_devops,
    handle_stage_errors,
    handle_stage_finalize,
    handle_stage_guide_gen,
    handle_stage_maintainability,
    handle_stage_parse,
    handle_stage_perf,
    handle_stage_reliability,
    handle_stage_rules,
    handle_stage_score,
    handle_stage_simulation,
    handle_start_analysis,
)
from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile
from app.domain.entities.finding import Finding
from app.domain.entities.score import Score
from app.domain.events import (
    AnalysisProgressed,
    EngineCompleted,
    EngineFailed,
    EngineStarted,
)
from app.domain.rules.base import RuleViolation
from app.domain.rules.registry import create_default_registry
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.git.repository_fetcher import RepositoryFetcher
from app.infrastructure.messaging.producer import EventProducer
from app.infrastructure.parsers.base import ChainedParser
from app.infrastructure.parsers.csharp_parser import CSharpParser
from app.infrastructure.parsers.elixir_parser import ElixirParser
from app.infrastructure.parsers.go_parser import GoParser
from app.infrastructure.parsers.java_parser import JavaParser
from app.infrastructure.parsers.kotlin_parser import KotlinParser
from app.infrastructure.parsers.mern_parser import MernParser
from app.infrastructure.parsers.php_parser import PhpParser
from app.infrastructure.parsers.python_parser import PythonParser
from app.infrastructure.parsers.ruby_parser import RubyParser
from app.infrastructure.parsers.rust_parser import RustParser
from app.infrastructure.scorer import ProductionReadinessScorer
from app.infrastructure.storage.s3 import S3Storage
from app.workers.dead_code.detector import DeadCodeFinding
from app.workers.devops.models import DevOpsFinding
from app.workers.errors.scanner import ErrorFinding
from app.workers.maintainability.models import MaintainabilityFinding
from app.workers.perf.rpm_calculator import PerformanceMetrics
from app.workers.reliability.models import ReliabilityFinding

logger = get_logger(__name__)

_PARSER: ChainedParser | None = None
_REGISTRY = create_default_registry()
_SCORER = ProductionReadinessScorer()

_STAGE_STATUS: dict[str, str] = {
    "start": "cloning",
    "clone": "clone",
    "churn": "churn",
    "parse": "parsing",
    "rules": "rules",
    "save_findings": "save_findings",
    "dead_code": "dead_code",
    "errors": "errors",
    "reliability": "reliability",
    "maintainability": "maintainability",
    "devops": "devops",
    "perf": "perf",
    "simulation": "simulation",
    "score": "scoring",
    "guide_gen": "guide_gen",
    "ai_enrich": "ai_enrich",
    "finalize": "finalize",
}

_STAGE_ENGINE: dict[str, str | None] = {
    "start": None,
    "clone": None,
    "churn": None,
    "parse": None,
    "rules": None,
    "save_findings": None,
    "dead_code": "dead_code",
    "errors": "error_detection",
    "reliability": "reliability",
    "maintainability": "maintainability",
    "devops": "devops",
    "perf": "performance",
    "simulation": "simulation",
    "score": None,
    "guide_gen": None,
    "ai_enrich": None,
    "finalize": None,
}

_STAGE_ENGINES: dict[str, list[str]] = {
    "rules": ["security"],
}

ALL_ENGINES = {
    "security",
    "maintainability",
    "reliability",
    "devops",
    "dead_code",
    "error_detection",
    "performance",
    "simulation",
}

_STAGE_PROGRESS: dict[str, int] = {
    "start": 10,
    "clone": 15,
    "churn": 18,
    "parse": 25,
    "rules": 50,
    "save_findings": 65,
    "dead_code": 75,
    "errors": 78,
    "reliability": 80,
    "maintainability": 82,
    "devops": 84,
    "perf": 87,
    "simulation": 90,
    "score": 93,
    "guide_gen": 95,
    "ai_enrich": 98,
    "finalize": 100,
}


def _get_parser() -> ChainedParser:
    global _PARSER
    if _PARSER is None:
        p = ChainedParser()
        p.register(PythonParser())
        p.register(MernParser())
        p.register(GoParser())
        p.register(CSharpParser())
        p.register(JavaParser())
        p.register(PhpParser())
        p.register(RubyParser())
        p.register(RustParser())
        p.register(KotlinParser())
        p.register(ElixirParser())
        _PARSER = p
    return _PARSER


async def _push_stage_progress(state: dict[str, object], stage_name: str) -> None:
    if not state.get("job_id"):
        return
    job_id = cast(UUID, state["job_id"])
    pct = _STAGE_PROGRESS.get(stage_name, 50)
    status = _STAGE_STATUS.get(stage_name, stage_name)
    engine_statuses = cast(dict[str, str] | None, state.get("engine_statuses"))
    try:
        await asyncio.wait_for(
            _push_progress(
                job_id,
                status,
                pct,
                f"Running {stage_name}...",
                engine_statuses=engine_statuses,
            ),
            timeout=10,
        )
    except Exception:
        logger.warning("push_progress_failed", stage=stage_name)
    try:
        producer = EventProducer()
        await asyncio.wait_for(
            producer.publish(
                AnalysisProgressed(
                    job_id=job_id,
                    status=status,
                    progress_pct=pct,
                )
            ),
            timeout=5,
        )
    except Exception:
        logger.warning("publish_progress_failed", stage=stage_name)


async def run_full_analysis(cmd_dict: dict[str, object]) -> dict[str, object]:
    """Execute the complete analysis pipeline in the background.

    Called by the API layer after creating a job via asyncio.create_task.
    Runs every stage sequentially, passing an in-memory state dict between
    stages. Each stage is wrapped with error handling so the job is marked
    as failed immediately and the pipeline halts.

    Args:
        cmd_dict: Serialized StartAnalysisCommand fields.
                   May include 'job_id' if the job was already created
                   by the API router.

    Returns:
        Dict with job_id and report summary.
    """
    job_id_str = cmd_dict.pop("job_id", None)
    cmd = StartAnalysisCommand(**cmd_dict)  # type: ignore[arg-type]
    state: dict[str, object] = {}
    if job_id_str:
        state["job_id"] = UUID(cast(str, job_id_str))

    try:
        await _run_pipeline(cmd, state)
    except Exception:
        # Stage-level handlers already called _handle_failure_async;
        # just log and re-raise so asyncio doesn't swallow it silently.
        logger.exception("pipeline_aborted")
        raise

    score_raw = state.get("score")
    overall_score = score_raw.overall if isinstance(score_raw, Score) else None
    return {
        "job_id": str(cast(UUID, state["job_id"])),
        "status": "completed",
        "overall_score": overall_score,
        "findings_count": len(cast(list[object], state.get("findings", []))),
    }


async def _publish_engine_event(
    job_id: UUID, engine_name: str, new_status: str, error_message: str = ""
) -> None:
    try:
        producer = EventProducer()
        if new_status == "running":
            event = EngineStarted(job_id=job_id, engine_name=engine_name)
        elif new_status == "completed":
            event = EngineCompleted(job_id=job_id, engine_name=engine_name)
        elif new_status == "failed":
            event = EngineFailed(
                job_id=job_id, engine_name=engine_name, error_message=error_message
            )
        else:
            return
        await asyncio.wait_for(producer.publish(event), timeout=5)
    except Exception:
        logger.warning("publish_engine_event_failed", engine=engine_name)


async def _run_pipeline(cmd: StartAnalysisCommand, state: dict[str, object]) -> None:
    """Execute all pipeline stages sequentially with per-stage error handling.

    Each stage is wrapped in try/except so a failure marks the job as failed
    immediately with a clear message and halts the pipeline.
    """
    state["_pipeline_start"] = time.monotonic()
    state["engine_statuses"] = dict.fromkeys(ALL_ENGINES, "pending")
    for stage_name, stage_fn, stage_args in (
        ("start", _stage_start, (cmd,)),
        ("clone", _stage_clone, ()),
        ("churn", _stage_churn, ()),
        ("parse", _stage_parse, ()),
        ("rules", _stage_rules, ()),
        ("save_findings", _stage_save_findings, ()),
        ("dead_code", _stage_dead_code, ()),
        ("errors", _stage_errors, ()),
        ("reliability", _stage_reliability, ()),
        ("maintainability", _stage_maintainability, ()),
        ("devops", _stage_devops, ()),
        ("perf", _stage_perf, ()),
        ("simulation", _stage_simulation, ()),
        ("score", _stage_score, ()),
        ("guide_gen", _stage_guide_gen, ()),
        ("ai_enrich", _stage_ai_enrich, ()),
        ("finalize", _stage_finalize, ()),
    ):
        state["_last_stage"] = stage_name
        engine_ids = _STAGE_ENGINES.get(stage_name, [])
        single_engine_id = _STAGE_ENGINE.get(stage_name)
        engine_ids = engine_ids + ([single_engine_id] if single_engine_id else [])
        job_id = cast(UUID, state.get("job_id"))
        for eid in engine_ids:
            cast(dict[str, str], state["engine_statuses"])[eid] = "running"
            state[f"_engine_start_{eid}"] = time.monotonic()
            if job_id:
                await _publish_engine_event(job_id, eid, "running")
        await _push_stage_progress(state, stage_name)
        try:
            if stage_args:
                await stage_fn(state, *stage_args)  # type: ignore[call-arg]
            else:
                await stage_fn(state)  # type: ignore[call-arg]
            for eid in engine_ids:
                cast(dict[str, str], state["engine_statuses"])[eid] = "completed"
                if job_id:
                    await _publish_engine_event(job_id, eid, "completed")
        except Exception:
            for eid in engine_ids:
                cast(dict[str, str], state["engine_statuses"])[eid] = "failed"
                if job_id:
                    await _publish_engine_event(
                        job_id, eid, "failed", traceback.format_exc()
                    )
            if job_id:
                await _handle_failure_async(
                    job_id=job_id,
                    stage=stage_name,
                    error_message=traceback.format_exc(),
                )
            raise


async def _stage_start(state: dict[str, object], cmd: StartAnalysisCommand) -> None:
    state["_last_stage"] = "start"

    async with UnitOfWork() as uow:
        producer = EventProducer()

        # If job_id was already created by the API router, use it
        if "job_id" in state:
            job_id = cast(UUID, state["job_id"])
        else:
            job_id = await handle_start_analysis(cmd, uow, producer)

        await uow.jobs.update_status(
            job_id,
            "cloning",
            progress_pct=10,
            progress_message="Starting analysis pipeline...",
            started_at=datetime.utcnow(),
        )
        await uow.commit()
        state["job_id"] = job_id

    logger.info(
        "pipeline_stage_complete",
        stage="start",
        job_id=str(cast(UUID, state["job_id"])),
    )


async def _stage_clone(state: dict[str, object]) -> None:
    state["_last_stage"] = "clone"
    job_id = cast(UUID, state["job_id"])
    cmd = ProcessStageCommand(job_id=job_id, stage="clone")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        fetcher = RepositoryFetcher()
        result = await handle_stage_clone(cmd, uow, fetcher, producer)
        await uow.commit()
        state.update(result)

    logger.info(
        "pipeline_stage_complete",
        stage="clone",
        job_id=str(job_id),
        files=state.get("total_files"),
        languages=state.get("languages"),
    )


async def _stage_churn(state: dict[str, object]) -> None:
    state["_last_stage"] = "churn"
    job_id = cast(UUID, state["job_id"])
    repo_path = cast(str, state.get("repo_path", ""))
    cmd = ProcessStageCommand(job_id=job_id, stage="churn")

    if not repo_path:
        logger.warning("churn_skipped", reason="no_repo_path", job_id=str(job_id))
        return

    async with UnitOfWork() as uow:
        job = await uow.jobs.get_by_id(job_id)
        clone_depth = cast(int, job.get("depth", 1)) if job else 1

        if clone_depth <= 1:
            logger.info("churn_skipped", reason="shallow_clone", depth=clone_depth, job_id=str(job_id))
            return

        result = await handle_stage_churn(cmd, uow, repo_path, clone_depth)
        await uow.commit()
        state["churn_results"] = result

    logger.info(
        "pipeline_stage_complete",
        stage="churn",
        job_id=str(job_id),
        hotspots=len(cast(list[object], state.get("churn_results", []))),
    )


async def _stage_parse(state: dict[str, object]) -> None:
    state["_last_stage"] = "parse"
    job_id = cast(UUID, state["job_id"])
    repo_path = cast(str, state["repo_path"])
    files = cast(list[dict[str, object]], state["files"])
    cmd = ProcessStageCommand(job_id=job_id, stage="parse")
    parser = _get_parser()

    async with UnitOfWork() as uow:
        producer = EventProducer()
        metadata, parsed_files = await handle_stage_parse(
            cmd,
            parser,
            uow,
            producer,
            repo_path,
            files,
        )
        await handle_save_analysis_metadata(
            job_id=job_id,
            parsed_files_metadata=metadata,
            languages=cast(list[str], state.get("languages", [])),
            frameworks=cast(list[str], state.get("frameworks", [])),
            uow=uow,
        )
        await uow.commit()

        state["parsed_files_metadata"] = metadata
        state["_parsed_files"] = parsed_files

    logger.info(
        "pipeline_stage_complete",
        stage="parse",
        job_id=str(job_id),
        parsed=len(cast(list[object], state.get("parsed_files_metadata", []))),
    )


async def _stage_rules(state: dict[str, object]) -> None:
    state["_last_stage"] = "rules"
    job_id = cast(UUID, state["job_id"])
    parsed_files = cast(list[ParsedFile], state.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=job_id, stage="rules")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        summary, violations = await handle_stage_rules(
            cmd,
            _REGISTRY,
            uow,
            producer,
            parsed_files,
        )
        await uow.commit()
        state["rule_violations_summary"] = summary
        state["_violations"] = violations

    logger.info(
        "pipeline_stage_complete",
        stage="rules",
        job_id=str(job_id),
        violations=len(cast(list[object], state.get("rule_violations_summary", []))),
    )


async def _stage_save_findings(state: dict[str, object]) -> None:
    state["_last_stage"] = "save_findings"
    job_id = cast(UUID, state["job_id"])
    violations = cast(list[RuleViolation], state["_violations"])
    cmd = ProcessStageCommand(job_id=job_id, stage="save_findings")

    async with UnitOfWork() as uow:
        job = await uow.jobs.get_by_id(cmd.job_id)
        if not job:
            return

        findings = await handle_save_findings(cmd, uow, violations, job)
        await uow.commit()
        state["findings"] = findings

    logger.info(
        "pipeline_stage_complete",
        stage="save_findings",
        job_id=str(job_id),
        findings=len(cast(list[object], state.get("findings", []))),
    )


async def _stage_score(state: dict[str, object]) -> None:
    state["_last_stage"] = "score"
    job_id = cast(UUID, state["job_id"])
    violations = cast(list[RuleViolation], state.get("_violations", []))
    dead_code_results_raw = state.get("dead_code_results")
    dead_code_results = (
        cast(list[DeadCodeFinding], dead_code_results_raw)
        if dead_code_results_raw is not None
        else None
    )
    error_results_raw = state.get("error_results")
    error_results = (
        cast(list[ErrorFinding], error_results_raw)
        if error_results_raw is not None
        else None
    )
    perf_metrics_raw = state.get("perf_metrics")
    perf_metrics = (
        cast(PerformanceMetrics, perf_metrics_raw)
        if perf_metrics_raw is not None
        else None
    )
    simulation_results_raw = state.get("simulation_results")
    simulation_results = (
        cast(list[dict[str, object]], simulation_results_raw)
        if simulation_results_raw is not None
        else None
    )
    reliability_results_raw = state.get("reliability_results")
    reliability_results = (
        cast(list[ReliabilityFinding], reliability_results_raw)
        if reliability_results_raw is not None
        else None
    )
    devops_results_raw = state.get("devops_results")
    devops_results = (
        cast(list[DevOpsFinding], devops_results_raw)
        if devops_results_raw is not None
        else None
    )
    maintainability_results_raw = state.get("maintainability_results")
    maintainability_results = (
        cast(list[MaintainabilityFinding], maintainability_results_raw)
        if maintainability_results_raw is not None
        else None
    )
    total_files = cast(int, state.get("total_files", 0))
    cmd = ProcessStageCommand(job_id=job_id, stage="score", total_files=total_files)

    async with UnitOfWork() as uow:
        producer = EventProducer()
        engine_statuses = cast(dict[str, str] | None, state.get("engine_statuses"))
        score = await handle_stage_score(
            cmd,
            _SCORER,
            uow,
            producer,
            violations,
            dead_code_results=dead_code_results,
            error_results=error_results,
            reliability_results=reliability_results,
            devops_results=devops_results,
            maintainability_results=maintainability_results,
            perf_metrics=perf_metrics,
            simulation_results=simulation_results,
            engine_statuses=engine_statuses,
        )
        await uow.commit()
        state["score"] = score

    logger.info(
        "pipeline_stage_complete",
        stage="score",
        job_id=str(job_id),
        score=cast(Score, state["score"]).overall if state.get("score") else None,
    )


async def _stage_dead_code(state: dict[str, object]) -> None:
    state["_last_stage"] = "dead_code"
    job_id = cast(UUID, state["job_id"])
    parsed_files = cast(list[ParsedFile], state.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=job_id, stage="dead_code")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        results = await handle_stage_dead_code(
            cmd,
            uow,
            producer,
            parsed_files,
        )
        await uow.commit()
        state["dead_code_results"] = results

    logger.info(
        "pipeline_stage_complete",
        stage="dead_code",
        job_id=str(job_id),
        count=len(cast(list[object], state.get("dead_code_results", []))),
    )


async def _stage_errors(state: dict[str, object]) -> None:
    state["_last_stage"] = "errors"
    job_id = cast(UUID, state["job_id"])
    parsed_files = cast(list[ParsedFile], state.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=job_id, stage="errors")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        results = await handle_stage_errors(
            cmd,
            uow,
            producer,
            parsed_files,
        )
        await uow.commit()
        state["error_results"] = results

    logger.info(
        "pipeline_stage_complete",
        stage="errors",
        job_id=str(job_id),
        count=len(cast(list[object], state.get("error_results", []))),
    )


async def _stage_reliability(state: dict[str, object]) -> None:
    state["_last_stage"] = "reliability"
    job_id = cast(UUID, state["job_id"])
    parsed_files = cast(list[ParsedFile], state.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=job_id, stage="reliability")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        results = await handle_stage_reliability(
            cmd,
            uow,
            producer,
            parsed_files,
        )
        await uow.commit()
        state["reliability_results"] = results

    logger.info(
        "pipeline_stage_complete",
        stage="reliability",
        job_id=str(job_id),
        count=len(cast(list[object], state.get("reliability_results", []))),
    )


async def _stage_maintainability(state: dict[str, object]) -> None:
    state["_last_stage"] = "maintainability"
    job_id = cast(UUID, state["job_id"])
    parsed_files = cast(list[ParsedFile], state.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=job_id, stage="maintainability")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        results = await handle_stage_maintainability(
            cmd,
            uow,
            producer,
            parsed_files,
        )
        await uow.commit()
        state["maintainability_results"] = results

    logger.info(
        "pipeline_stage_complete",
        stage="maintainability",
        job_id=str(job_id),
        count=len(cast(list[object], state.get("maintainability_results", []))),
    )


async def _stage_devops(state: dict[str, object]) -> None:
    state["_last_stage"] = "devops"
    job_id = cast(UUID, state["job_id"])
    parsed_files = cast(list[ParsedFile], state.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=job_id, stage="devops")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        results = await handle_stage_devops(
            cmd,
            uow,
            producer,
            parsed_files,
        )
        await uow.commit()
        state["devops_results"] = results

    logger.info(
        "pipeline_stage_complete",
        stage="devops",
        job_id=str(job_id),
        count=len(cast(list[object], state.get("devops_results", []))),
    )


async def _stage_perf(state: dict[str, object]) -> None:
    state["_last_stage"] = "perf"
    job_id = cast(UUID, state["job_id"])
    parsed_files = cast(list[ParsedFile], state.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=job_id, stage="perf")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        metrics = await handle_stage_perf(
            cmd,
            uow,
            producer,
            parsed_files,
        )
        await uow.commit()
        state["perf_metrics"] = metrics

    logger.info(
        "pipeline_stage_complete",
        stage="perf",
        job_id=str(job_id),
        rpm=cast(PerformanceMetrics, state["perf_metrics"]).overall_rpm
        if state.get("perf_metrics")
        else None,
    )


async def _stage_simulation(state: dict[str, object]) -> None:
    state["_last_stage"] = "simulation"
    job_id = cast(UUID, state["job_id"])
    perf_metrics_raw = state.get("perf_metrics")
    perf_metrics = (
        cast(PerformanceMetrics, perf_metrics_raw)
        if perf_metrics_raw is not None
        else None
    )
    cmd = ProcessStageCommand(job_id=job_id, stage="simulation")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        results = await handle_stage_simulation(
            cmd,
            uow,
            producer,
            perf_metrics,
        )
        await uow.commit()
        state["simulation_results"] = results

    logger.info(
        "pipeline_stage_complete",
        stage="simulation",
        job_id=str(job_id),
        count=len(cast(list[object], state.get("simulation_results", []))),
    )


async def _stage_guide_gen(state: dict[str, object]) -> None:
    state["_last_stage"] = "guide_gen"
    job_id = cast(UUID, state["job_id"])
    violations = cast(list[RuleViolation], state.get("_violations", []))
    score_raw = state.get("score")
    score = cast(Score, score_raw) if score_raw is not None else Score(overall=0)
    perf_metrics_raw = state.get("perf_metrics")
    perf_metrics = (
        cast(PerformanceMetrics, perf_metrics_raw)
        if perf_metrics_raw is not None
        else None
    )
    simulation_results_raw = state.get("simulation_results")
    simulation_results = (
        cast(list[dict[str, object]], simulation_results_raw)
        if simulation_results_raw is not None
        else None
    )
    dead_code_results_raw = state.get("dead_code_results")
    dead_code_results = (
        cast(list[DeadCodeFinding], dead_code_results_raw)
        if dead_code_results_raw is not None
        else None
    )
    error_results_raw = state.get("error_results")
    error_results = (
        cast(list[ErrorFinding], error_results_raw)
        if error_results_raw is not None
        else None
    )
    reliability_results_raw = state.get("reliability_results")
    reliability_results: list[ReliabilityFinding] | None = (
        cast(list[ReliabilityFinding], reliability_results_raw)
        if reliability_results_raw is not None
        else None
    )
    devops_results_raw = state.get("devops_results")
    devops_results: list[DevOpsFinding] | None = (
        cast(list[DevOpsFinding], devops_results_raw)
        if devops_results_raw is not None
        else None
    )
    maintainability_results_raw = state.get("maintainability_results")
    maintainability_results: list[MaintainabilityFinding] | None = (
        cast(list[MaintainabilityFinding], maintainability_results_raw)
        if maintainability_results_raw is not None
        else None
    )
    cmd = ProcessStageCommand(job_id=job_id, stage="guide_gen")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        guide = await handle_stage_guide_gen(
            cmd,
            uow,
            producer,
            violations,
            score,
            perf_metrics=perf_metrics,
            simulation_results=simulation_results,
            dead_code_results=dead_code_results,
            error_results=error_results,
            reliability_results=reliability_results,
            devops_results=devops_results,
            maintainability_results=maintainability_results,
        )
        await uow.commit()
        state["enterprise_guide"] = guide

    logger.info(
        "pipeline_stage_complete",
        stage="guide_gen",
        job_id=str(job_id),
    )


async def _stage_ai_enrich(state: dict[str, object]) -> None:
    state["_last_stage"] = "ai_enrich"
    job_id = cast(UUID, state["job_id"])
    findings = cast(list[Finding], state.get("findings", []))
    score_raw = state.get("score")
    score = cast(Score, score_raw) if score_raw is not None else None
    languages = cast(list[str] | None, state.get("languages"))
    frameworks = cast(list[str] | None, state.get("frameworks"))
    cmd = ProcessStageCommand(job_id=job_id, stage="ai_enrich")

    async with UnitOfWork() as uow:
        result = await handle_stage_ai_enrich(
            cmd,
            uow,
            findings,
            score=score,
            languages=languages,
            frameworks=frameworks,
        )
        await uow.commit()
        if result:
            state["ai_enrichment"] = result

    logger.info(
        "pipeline_stage_complete",
        stage="ai_enrich",
        job_id=str(job_id),
        enriched=len(cast(list[object], result.get("findings", []))) if result else 0,
    )


async def _stage_finalize(state: dict[str, object]) -> None:
    state["_last_stage"] = "finalize"
    job_id = cast(UUID, state["job_id"])
    score_raw = state.get("score")
    score = cast(Score, score_raw) if score_raw is not None else Score(overall=0)
    findings = cast(list[Finding], state.get("findings", []))
    languages = cast(list[str], state.get("languages", []))
    language_breakdown = cast(list[dict], state.get("language_breakdown", []))
    total_files = cast(int, state.get("total_files", 0))
    total_lines = cast(int, state.get("total_lines", 0))
    duration_seconds = int(
        time.monotonic() - cast(float, state.get("_pipeline_start", 0))
    )
    cmd = ProcessStageCommand(job_id=job_id, stage="finalize")

    async with UnitOfWork() as uow:
        job = await uow.jobs.get_by_id(cmd.job_id)
        if not job:
            return
        producer = EventProducer()
        storage = S3Storage()
        report = await handle_stage_finalize(
            cmd,
            uow,
            producer,
            storage,
            job,
            score,
            findings,
            languages,
            language_breakdown,
            total_files,
            total_lines,
            duration_seconds,
        )
        await uow.commit()
        state["report"] = report.to_dict()

    logger.info(
        "pipeline_stage_complete",
        stage="finalize",
        job_id=str(job_id),
    )


async def _handle_failure_async(
    job_id: UUID,
    stage: str,
    error_message: str,
) -> None:
    async with UnitOfWork() as uow:
        producer = EventProducer()
        await handle_analysis_failure(
            job_id,
            stage,
            error_message,
            uow,
            producer,
        )
        await uow.commit()
