"""Full analysis pipeline orchestrator.

Runs all stages sequentially within a single Celery task.
Each stage calls the same handler functions used by individual tasks,
but shares state in-memory instead of passing through the chain.
"""

from uuid import UUID

from celery import shared_task

from app.application.analysis.commands import (
    ProcessStageCommand,
    StartAnalysisCommand,
)
from app.application.analysis.handler import (
    handle_analysis_failure,
    handle_save_findings,
    handle_stage_clone,
    handle_stage_dead_code,
    handle_stage_errors,
    handle_stage_finalize,
    handle_stage_guide_gen,
    handle_stage_parse,
    handle_stage_perf,
    handle_stage_rules,
    handle_stage_score,
    handle_stage_simulation,
    handle_start_analysis,
)
from app.application.tasks.runner import run_async
from app.core.logging import get_logger
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

logger = get_logger(__name__)

_PARSER: ChainedParser | None = None
_REGISTRY = create_default_registry()
_SCORER = ProductionReadinessScorer()


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


@shared_task(bind=True, max_retries=2, default_retry_delay=120, acks_late=True)
def run_full_analysis(self, cmd_dict: dict) -> dict:
    """Execute the complete analysis pipeline in a single task.

    Called by the API layer after creating a job. Runs every
    stage sequentially, passing an in-memory state dict between
    stages. On failure, marks the job as failed and publishes
    the failure event.

    Args:
        cmd_dict: Serialized StartAnalysisCommand fields.
                   May include 'job_id' if the job was already created
                   by the API router.

    Returns:
        Dict with job_id and report summary.
    """
    job_id_str = cmd_dict.pop("job_id", None)
    cmd = StartAnalysisCommand(**cmd_dict)
    state: dict = {}
    if job_id_str:
        state["job_id"] = UUID(job_id_str)

    try:
        _run_pipeline(cmd, state)
        return {
            "job_id": str(state["job_id"]),
            "status": "completed",
            "overall_score": state.get("score").overall  # type: ignore[union-attr]
            if state.get("score")
            else None,
            "findings_count": len(state.get("findings", [])),
        }
    except Exception as exc:
        logger.error("pipeline_failed", error=str(exc))
        if "job_id" in state:
            _handle_failure_sync(
                job_id=state["job_id"],
                stage=state.get("_last_stage", "unknown"),
                error_message=str(exc),
            )
        raise self.retry(exc=exc)


def _run_pipeline(cmd: StartAnalysisCommand, state: dict) -> None:
    """Execute all pipeline stages sequentially."""
    _stage_start(cmd, state)
    _stage_clone(state)
    _stage_parse(state)
    _stage_rules(state)
    _stage_save_findings(state)
    _stage_score(state)
    _stage_dead_code(state)
    _stage_errors(state)
    _stage_perf(state)
    _stage_simulation(state)
    _stage_guide_gen(state)
    _stage_finalize(state)


def _stage_start(cmd: StartAnalysisCommand, state: dict) -> None:
    state["_last_stage"] = "start"

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()

            # If job_id was already created by the API router, use it
            if "job_id" in state:
                job_id = state["job_id"]
            else:
                job_id = await handle_start_analysis(cmd, uow, producer)

            await uow.jobs.update_status(
                job_id, "cloning", progress_pct=10,
                progress_message="Starting analysis pipeline...",
            )
            await uow.commit()
            state["job_id"] = job_id

    run_async(_run())
    logger.info("pipeline_stage_complete", stage="start", job_id=str(state["job_id"]))


def _stage_clone(state: dict) -> None:
    state["_last_stage"] = "clone"
    job_id = state["job_id"]
    cmd = ProcessStageCommand(job_id=job_id, stage="clone")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            fetcher = RepositoryFetcher()
            result = await handle_stage_clone(cmd, uow, fetcher, producer)
            await uow.commit()
            state.update(result)

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="clone", job_id=str(job_id),
        files=state.get("total_files"),
        languages=state.get("languages"),
    )


def _stage_parse(state: dict) -> None:
    state["_last_stage"] = "parse"
    job_id = state["job_id"]
    repo_path = state["repo_path"]
    files = state["files"]
    cmd = ProcessStageCommand(job_id=job_id, stage="parse")
    parser = _get_parser()

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            metadata = await handle_stage_parse(
                cmd, parser, uow, producer, repo_path, files,
            )
            await uow.commit()

            parsed_files = []
            for f in files:
                pf = await parser.parse(f["path"], f["content"])
                parsed_files.append(pf)

            state["parsed_files_metadata"] = metadata
            state["_parsed_files"] = parsed_files

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="parse", job_id=str(job_id),
        parsed=len(state.get("parsed_files_metadata", [])),
    )


def _stage_rules(state: dict) -> None:
    state["_last_stage"] = "rules"
    job_id = state["job_id"]
    parsed_files = state.get("_parsed_files", [])
    cmd = ProcessStageCommand(job_id=job_id, stage="rules")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            summary = await handle_stage_rules(
                cmd, _REGISTRY, uow, producer, parsed_files,
            )
            await uow.commit()
            state["rule_violations_summary"] = summary

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="rules", job_id=str(job_id),
        violations=len(state.get("rule_violations_summary", [])),
    )


def _stage_save_findings(state: dict) -> None:
    state["_last_stage"] = "save_findings"
    job_id = state["job_id"]
    parsed_files = state.get("_parsed_files", [])
    cmd = ProcessStageCommand(job_id=job_id, stage="save_findings")
    registry = _REGISTRY

    async def _run():
        async with UnitOfWork() as uow:
            job = await uow.jobs.get_by_id(cmd.job_id)
            if not job:
                return

            violations: list[RuleViolation] = []
            for pf in parsed_files:
                ast_data = pf.ast_data
                ast_data["functions"] = pf.functions
                ast_data["classes"] = pf.classes
                ast_data["imports"] = pf.imports
                ast_data["routes"] = pf.routes
                applicable = registry.filter_for_file(pf.path, pf.language)
                for rule in applicable:
                    try:
                        v = await rule.analyze(pf.path, pf.content, ast_data)
                        violations.extend(v)
                    except Exception:
                        logger.warning(
                            "rule_failed", rule_id=rule.rule_id,
                            file=pf.path, job_id=str(job_id),
                        )

            findings = await handle_save_findings(cmd, uow, violations, job)
            await uow.commit()
            state["_violations"] = violations
            state["findings"] = findings

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="save_findings", job_id=str(job_id),
        findings=len(state.get("findings", [])),
    )


def _stage_score(state: dict) -> None:
    state["_last_stage"] = "score"
    job_id = state["job_id"]
    violations = state.get("_violations", [])
    cmd = ProcessStageCommand(job_id=job_id, stage="score")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            score = await handle_stage_score(
                cmd, _SCORER, uow, producer, violations,
            )
            await uow.commit()
            state["score"] = score

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="score", job_id=str(job_id),
        score=state["score"].overall if state.get("score") else None,
    )


def _stage_dead_code(state: dict) -> None:
    state["_last_stage"] = "dead_code"
    job_id = state["job_id"]
    parsed_files = state.get("_parsed_files", [])
    cmd = ProcessStageCommand(job_id=job_id, stage="dead_code")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            results = await handle_stage_dead_code(
                cmd, uow, producer, parsed_files,
            )
            await uow.commit()
            state["dead_code_results"] = results

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="dead_code", job_id=str(job_id),
        count=len(state.get("dead_code_results", [])),
    )


def _stage_errors(state: dict) -> None:
    state["_last_stage"] = "errors"
    job_id = state["job_id"]
    parsed_files = state.get("_parsed_files", [])
    cmd = ProcessStageCommand(job_id=job_id, stage="errors")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            results = await handle_stage_errors(
                cmd, uow, producer, parsed_files,
            )
            await uow.commit()
            state["error_results"] = results

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="errors", job_id=str(job_id),
        count=len(state.get("error_results", [])),
    )


def _stage_perf(state: dict) -> None:
    state["_last_stage"] = "perf"
    job_id = state["job_id"]
    parsed_files = state.get("_parsed_files", [])
    cmd = ProcessStageCommand(job_id=job_id, stage="perf")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            metrics = await handle_stage_perf(
                cmd, uow, producer, parsed_files,
            )
            await uow.commit()
            state["perf_metrics"] = metrics

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="perf", job_id=str(job_id),
        rpm=state["perf_metrics"].overall_rpm if state.get("perf_metrics") else None,
    )


def _stage_simulation(state: dict) -> None:
    state["_last_stage"] = "simulation"
    job_id = state["job_id"]
    perf_metrics = state.get("perf_metrics")
    cmd = ProcessStageCommand(job_id=job_id, stage="simulation")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            results = await handle_stage_simulation(
                cmd, uow, producer, perf_metrics,
            )
            await uow.commit()
            state["simulation_results"] = results

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="simulation", job_id=str(job_id),
        count=len(state.get("simulation_results", [])),
    )


def _stage_guide_gen(state: dict) -> None:
    state["_last_stage"] = "guide_gen"
    job_id = state["job_id"]
    violations = state.get("_violations", [])
    score = state.get("score")
    perf_metrics = state.get("perf_metrics")
    simulation_results = state.get("simulation_results")
    dead_code_results = state.get("dead_code_results")
    error_results = state.get("error_results")
    cmd = ProcessStageCommand(job_id=job_id, stage="guide_gen")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            guide = await handle_stage_guide_gen(
                cmd, uow, producer, violations, score,
                perf_metrics=perf_metrics,
                simulation_results=simulation_results,
                dead_code_results=dead_code_results,
                error_results=error_results,
            )
            await uow.commit()
            state["enterprise_guide"] = guide

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="guide_gen", job_id=str(job_id),
    )


def _stage_finalize(state: dict) -> None:
    state["_last_stage"] = "finalize"
    job_id = state["job_id"]
    score = state.get("score")
    findings = state.get("findings", [])
    languages = state.get("languages", [])
    total_files = state.get("total_files", 0)
    total_lines = state.get("total_lines", 0)
    cmd = ProcessStageCommand(job_id=job_id, stage="finalize")

    async def _run():
        async with UnitOfWork() as uow:
            job = await uow.jobs.get_by_id(cmd.job_id)
            if not job:
                return
            producer = EventProducer()
            storage = S3Storage()
            report = await handle_stage_finalize(
                cmd, uow, producer, storage, job, score, findings,
                languages, total_files, total_lines, 0,
            )
            await uow.commit()
            state["report"] = report.to_dict()

    run_async(_run())
    logger.info(
        "pipeline_stage_complete",
        stage="finalize", job_id=str(job_id),
    )


def _handle_failure_sync(
    job_id: UUID, stage: str, error_message: str,
) -> None:
    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            await handle_analysis_failure(
                job_id, stage, error_message, uow, producer,
            )
            await uow.commit()

    run_async(_run())
