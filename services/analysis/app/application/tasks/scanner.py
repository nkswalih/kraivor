from typing import cast
from uuid import UUID

from app.application.analysis.commands import ProcessStageCommand, StartAnalysisCommand
from app.application.analysis.handler import (
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
from app.core.constants import Category, Severity
from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile
from app.domain.entities.finding import Finding
from app.domain.entities.score import Score
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
from app.workers.errors.scanner import ErrorFinding
from app.workers.perf.rpm_calculator import PerformanceMetrics

logger = get_logger(__name__)

_PARSER: ChainedParser | None = None
_REGISTRY = create_default_registry()


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


async def task_start_analysis(cmd_dict: dict[str, object]) -> str:
    cmd = StartAnalysisCommand(**cmd_dict)  # type: ignore[arg-type]

    async with UnitOfWork() as uow:
        producer = EventProducer()
        job_id = await handle_start_analysis(cmd, uow, producer)
        await uow.commit()
        return str(job_id)


async def task_clone(job_id: str) -> dict[str, object]:
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="clone")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        fetcher = RepositoryFetcher()
        result = await handle_stage_clone(cmd, uow, fetcher, producer)
        await uow.commit()
        result["job_id"] = job_id
        return result


async def task_parse(prev_result: dict[str, object]) -> dict[str, object]:
    job_id = cast(str, prev_result["job_id"])
    repo_path = cast(str, prev_result["repo_path"])
    files = cast(list[dict[str, object]], prev_result["files"])
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="parse")
    parser = _get_parser()

    async with UnitOfWork() as uow:
        producer = EventProducer()
        metadata = await handle_stage_parse(
            cmd,
            parser,
            uow,
            producer,
            repo_path,
            files,
        )
        await uow.commit()

    prev_result["parsed_files"] = metadata
    return prev_result


async def task_rules(prev_result: dict[str, object]) -> dict[str, object]:
    job_id = cast(str, prev_result["job_id"])
    files = cast(list[dict[str, object]], prev_result["files"])
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="rules")
    parser = _get_parser()

    async with UnitOfWork() as uow:
        parsed_files = []
        for f in files:
            pf = await parser.parse(cast(str, f["path"]), cast(str, f["content"]))
            parsed_files.append(pf)

        producer = EventProducer()
        summary = await handle_stage_rules(
            cmd,
            _REGISTRY,
            uow,
            producer,
            parsed_files,
        )
        await uow.commit()

    prev_result["rule_violations"] = summary
    prev_result["_parsed_files"] = parsed_files
    return prev_result


async def task_save_findings(prev_result: dict[str, object]) -> dict[str, object]:
    job_id = cast(str, prev_result["job_id"])
    parsed_files = cast(list[ParsedFile], prev_result.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="save_findings")

    async with UnitOfWork() as uow:
        job = await uow.jobs.get_by_id(cmd.job_id)
        if not job:
            return prev_result

        violations = []
        for pf in parsed_files:
            ast_data = pf.ast_data
            ast_data["functions"] = pf.functions
            ast_data["classes"] = pf.classes
            ast_data["imports"] = pf.imports
            ast_data["routes"] = pf.routes
            applicable = _REGISTRY.filter_for_file(pf.path, pf.language)
            for rule in applicable:
                try:
                    v = await rule.analyze(pf.path, pf.content, ast_data)
                    violations.extend(v)
                except Exception:
                    logger.warning(
                        "rule_failed",
                        rule_id=rule.rule_id,
                        file=pf.path,
                        job_id=job_id,
                    )

        findings = await handle_save_findings(cmd, uow, violations, job)
        await uow.commit()

    rule_violations = [
        {
            "rule_id": v.rule_id,
            "severity": str(v.severity),
            "category": str(v.category),
            "title": v.title,
            "file_path": v.file_path,
            "line_start": v.line_start,
            "line_end": v.line_end,
            "score_impact": v.score_impact,
            "rpm_impact": v.rpm_impact,
            "breaks_at_users": v.breaks_at_users,
        }
        for v in violations
    ]
    prev_result["rule_violations"] = rule_violations
    prev_result["_findings"] = findings
    return prev_result


async def task_score(prev_result: dict[str, object]) -> dict[str, object]:
    job_id = cast(str, prev_result["job_id"])
    rule_violations = cast(
        list[dict[str, object]], prev_result.get("rule_violations", [])
    )
    total_files = cast(int, prev_result.get("total_files", 0))
    cmd = ProcessStageCommand(
        job_id=UUID(job_id), stage="score", total_files=total_files
    )

    from app.domain.rules.base import RuleViolation as RuleV

    violations = [
        RuleV(
            rule_id=cast(str, v["rule_id"]),
            category=cast(Category, v["category"]),
            severity=cast(Severity, v["severity"]),
            title=cast(str, v["title"]),
            file_path=cast(str, v["file_path"]),
            line_start=cast(int | None, v["line_start"]),
            line_end=cast(int | None, v["line_end"]),
            score_impact=cast(float, v["score_impact"]),
            rpm_impact=cast(int, v["rpm_impact"]),
            breaks_at_users=cast(int | None, v["breaks_at_users"]),
        )
        for v in rule_violations
    ]

    scorer = ProductionReadinessScorer()

    async with UnitOfWork() as uow:
        producer = EventProducer()
        score = await handle_stage_score(cmd, scorer, uow, producer, violations)
        await uow.commit()

    prev_result["score"] = score.to_dict()
    prev_result["_score_obj"] = score
    return prev_result


async def task_finalize(prev_result: dict[str, object]) -> dict[str, object]:
    job_id = cast(str, prev_result["job_id"])
    score_raw = prev_result.get("_score_obj")
    score = cast(Score, score_raw) if score_raw is not None else Score(overall=0)
    findings = cast(list[Finding], prev_result.get("_findings", []))
    languages = cast(list[str], prev_result.get("languages", []))
    total_files = cast(int, prev_result.get("total_files", 0))
    total_lines = cast(int, prev_result.get("total_lines", 0))
    duration_seconds = cast(int, prev_result.get("duration_seconds", 0))
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="finalize")

    async with UnitOfWork() as uow:
        job = await uow.jobs.get_by_id(cmd.job_id)
        if not job:
            return {"job_id": job_id, "report": None}
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
            total_files,
            total_lines,
            duration_seconds,
        )
        await uow.commit()

    return {"job_id": job_id, "report": report.to_dict()}


async def task_dead_code(prev_result: dict[str, object]) -> dict[str, object]:
    job_id = cast(str, prev_result["job_id"])
    parsed_files = cast(list[ParsedFile], prev_result.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="dead_code")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        results = await handle_stage_dead_code(cmd, uow, producer, parsed_files)
        await uow.commit()

    prev_result["dead_code_results"] = results
    return prev_result


async def task_errors(prev_result: dict[str, object]) -> dict[str, object]:
    job_id = cast(str, prev_result["job_id"])
    parsed_files = cast(list[ParsedFile], prev_result.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="errors")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        results = await handle_stage_errors(cmd, uow, producer, parsed_files)
        await uow.commit()

    prev_result["error_results"] = results
    return prev_result


async def task_perf(prev_result: dict[str, object]) -> dict[str, object]:
    job_id = cast(str, prev_result["job_id"])
    parsed_files = cast(list[ParsedFile], prev_result.get("_parsed_files", []))
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="perf")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        metrics = await handle_stage_perf(cmd, uow, producer, parsed_files)
        await uow.commit()

    prev_result["perf_metrics"] = metrics
    return prev_result


async def task_simulation(prev_result: dict[str, object]) -> dict[str, object]:
    job_id = cast(str, prev_result["job_id"])
    perf_metrics_raw = prev_result.get("perf_metrics")
    perf_metrics = (
        cast(PerformanceMetrics, perf_metrics_raw)
        if perf_metrics_raw is not None
        else None
    )
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="simulation")

    async with UnitOfWork() as uow:
        producer = EventProducer()
        results = await handle_stage_simulation(cmd, uow, producer, perf_metrics)
        await uow.commit()

    prev_result["simulation_results"] = results
    return prev_result


async def task_guide_gen(prev_result: dict[str, object]) -> dict[str, object]:
    job_id = cast(str, prev_result["job_id"])
    violations_raw = cast(
        list[dict[str, object]], prev_result.get("rule_violations", [])
    )
    score_raw = prev_result.get("score")
    perf_metrics_raw = prev_result.get("perf_metrics")
    simulation_results_raw = prev_result.get("simulation_results")
    dead_code_results_raw = prev_result.get("dead_code_results")
    error_results_raw = prev_result.get("error_results")

    violations = [
        RuleViolation(
            rule_id=cast(str, v["rule_id"]),
            category=cast(Category, v["category"]),
            severity=cast(Severity, v["severity"]),
            title=cast(str, v["title"]),
            file_path=cast(str, v["file_path"]),
            line_start=cast(int | None, v["line_start"]),
            line_end=cast(int | None, v["line_end"]),
            score_impact=cast(float, v["score_impact"]),
            rpm_impact=cast(int, v["rpm_impact"]),
            breaks_at_users=cast(int | None, v["breaks_at_users"]),
        )
        for v in violations_raw
    ]

    score = Score(**score_raw) if score_raw else Score(overall=100)  # type: ignore[arg-type]
    perf_metrics = (
        cast(PerformanceMetrics, perf_metrics_raw)
        if perf_metrics_raw is not None
        else None
    )
    simulation_results = (
        cast(list[dict[str, object]], simulation_results_raw)
        if simulation_results_raw is not None
        else None
    )
    dead_code_results = (
        cast(list[DeadCodeFinding], dead_code_results_raw)
        if dead_code_results_raw is not None
        else None
    )
    error_results = (
        cast(list[ErrorFinding], error_results_raw)
        if error_results_raw is not None
        else None
    )

    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="guide_gen")

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
        )
        await uow.commit()

    prev_result["enterprise_guide"] = guide
    return prev_result
