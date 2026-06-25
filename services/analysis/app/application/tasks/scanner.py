from uuid import UUID

from celery import shared_task

from app.application.analysis.commands import ProcessStageCommand
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
from app.application.tasks.runner import run_async
from app.core.constants import Severity
from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile
from app.domain.rules.base import RuleViolation
from app.domain.rules.registry import create_default_registry
from app.domain.entities.score import Score
from app.infrastructure.cache.redis import RedisCache
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
from app.infrastructure.storage.s3 import S3Storage

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_start_analysis(self, cmd_dict: dict) -> str:
    from app.application.analysis.commands import StartAnalysisCommand

    cmd = StartAnalysisCommand(**cmd_dict)

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            job_id = await handle_start_analysis(cmd, uow, producer)
            await uow.commit()
            return str(job_id)

    try:
        return run_async(_run())
    except Exception as exc:
        logger.error("task_start_analysis_failed", error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_clone(self, job_id: str) -> dict:
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="clone")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            fetcher = RepositoryFetcher()
            result = await handle_stage_clone(cmd, uow, fetcher, producer)
            await uow.commit()
            return result

    try:
        result = run_async(_run())
        result["job_id"] = job_id
        return result
    except Exception as exc:
        logger.error("task_clone_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_parse(self, prev_result: dict) -> dict:
    job_id = prev_result["job_id"]
    repo_path = prev_result["repo_path"]
    files = prev_result["files"]
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="parse")
    parser = _get_parser()

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            metadata = await handle_stage_parse(
                cmd, parser, uow, producer, repo_path, files,
            )
            await uow.commit()
            return metadata

    try:
        metadata = run_async(_run())
        prev_result["parsed_files"] = metadata
        return prev_result
    except Exception as exc:
        logger.error("task_parse_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_rules(self, prev_result: dict) -> dict:
    job_id = prev_result["job_id"]
    repo_path = prev_result["repo_path"]
    files = prev_result["files"]
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="rules")
    parser = _get_parser()

    async def _run():
        async with UnitOfWork() as uow:
            parsed_files = []
            for f in files:
                pf = await parser.parse(f["path"], f["content"])
                parsed_files.append(pf)

            producer = EventProducer()
            summary = await handle_stage_rules(
                cmd, _REGISTRY, uow, producer, parsed_files,
            )
            await uow.commit()
            return parsed_files, summary

    try:
        parsed_files, summary = run_async(_run())
        prev_result["rule_violations"] = summary
        prev_result["_parsed_files"] = parsed_files
        return prev_result
    except Exception as exc:
        logger.error("task_rules_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_save_findings(self, prev_result: dict) -> dict:
    job_id = prev_result["job_id"]
    parsed_files = prev_result.get("_parsed_files", [])
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="save_findings")

    async def _run():
        async with UnitOfWork() as uow:
            job = await uow.jobs.get_by_id(cmd.job_id)
            if not job:
                return []

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
                            "rule_failed", rule_id=rule.rule_id,
                            file=pf.path, job_id=job_id,
                        )

            findings = await handle_save_findings(cmd, uow, violations, job)
            await uow.commit()

            from app.domain.rules.base import RuleViolation

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
            return rule_violations, findings

    try:
        rule_violations, findings = run_async(_run())
        prev_result["rule_violations"] = rule_violations
        prev_result["_findings"] = findings
        return prev_result
    except Exception as exc:
        logger.error("task_save_findings_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_score(self, prev_result: dict) -> dict:
    job_id = prev_result["job_id"]
    rule_violations = prev_result.get("rule_violations", [])
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="score")

    from app.domain.rules.base import RuleViolation as RuleV

    violations = [
        RuleV(
            rule_id=v["rule_id"],
            category=v["category"],
            severity=v["severity"],
            title=v["title"],
            file_path=v["file_path"],
            line_start=v["line_start"],
            line_end=v["line_end"],
            score_impact=v["score_impact"],
            rpm_impact=v["rpm_impact"],
            breaks_at_users=v["breaks_at_users"],
        )
        for v in rule_violations
    ]

    from app.infrastructure.scorer import ProductionReadinessScorer

    scorer = ProductionReadinessScorer()

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            score = await handle_stage_score(cmd, scorer, uow, producer, violations)
            await uow.commit()
            return score

    try:
        score = run_async(_run())
        prev_result["score"] = score.to_dict()
        prev_result["_score_obj"] = score
        return prev_result
    except Exception as exc:
        logger.error("task_score_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_finalize(self, prev_result: dict) -> dict:
    job_id = prev_result["job_id"]
    score = prev_result.get("_score_obj")
    findings = prev_result.get("_findings", [])
    languages = prev_result.get("languages", [])
    total_files = prev_result.get("total_files", 0)
    total_lines = prev_result.get("total_lines", 0)
    duration_seconds = prev_result.get("duration_seconds", 0)
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="finalize")

    async def _run():
        async with UnitOfWork() as uow:
            job = await uow.jobs.get_by_id(cmd.job_id)
            if not job:
                return {}
            producer = EventProducer()
            storage = S3Storage()
            report = await handle_stage_finalize(
                cmd, uow, producer, storage, job, score, findings,
                languages, total_files, total_lines, duration_seconds,
            )
            await uow.commit()
            return report.to_dict()

    try:
        report_dict = run_async(_run())
        return {"job_id": job_id, "report": report_dict}
    except Exception as exc:
        logger.error("task_finalize_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_dead_code(self, prev_result: dict) -> dict:
    job_id = prev_result["job_id"]
    parsed_files: list[ParsedFile] = prev_result.get("_parsed_files", [])
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="dead_code")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            results = await handle_stage_dead_code(cmd, uow, producer, parsed_files)
            await uow.commit()
            return results

    try:
        results = run_async(_run())
        prev_result["dead_code_results"] = results
        return prev_result
    except Exception as exc:
        logger.error("task_dead_code_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_errors(self, prev_result: dict) -> dict:
    job_id = prev_result["job_id"]
    parsed_files: list[ParsedFile] = prev_result.get("_parsed_files", [])
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="errors")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            results = await handle_stage_errors(cmd, uow, producer, parsed_files)
            await uow.commit()
            return results

    try:
        results = run_async(_run())
        prev_result["error_results"] = results
        return prev_result
    except Exception as exc:
        logger.error("task_errors_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_perf(self, prev_result: dict) -> dict:
    job_id = prev_result["job_id"]
    parsed_files: list[ParsedFile] = prev_result.get("_parsed_files", [])
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="perf")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            metrics = await handle_stage_perf(cmd, uow, producer, parsed_files)
            await uow.commit()
            return metrics

    try:
        metrics = run_async(_run())
        prev_result["perf_metrics"] = metrics
        return prev_result
    except Exception as exc:
        logger.error("task_perf_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_simulation(self, prev_result: dict) -> dict:
    job_id = prev_result["job_id"]
    perf_metrics = prev_result.get("perf_metrics")
    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="simulation")

    async def _run():
        async with UnitOfWork() as uow:
            producer = EventProducer()
            results = await handle_stage_simulation(cmd, uow, producer, perf_metrics)
            await uow.commit()
            return results

    try:
        results = run_async(_run())
        prev_result["simulation_results"] = results
        return prev_result
    except Exception as exc:
        logger.error("task_simulation_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True)
def task_guide_gen(self, prev_result: dict) -> dict:
    job_id = prev_result["job_id"]
    violations_raw = prev_result.get("rule_violations", [])
    score_raw = prev_result.get("score")
    perf_metrics = prev_result.get("perf_metrics")
    simulation_results = prev_result.get("simulation_results")
    dead_code_results = prev_result.get("dead_code_results")
    error_results = prev_result.get("error_results")

    violations = [
        RuleViolation(
            rule_id=v["rule_id"],
            category=v["category"],
            severity=v["severity"],
            title=v["title"],
            file_path=v["file_path"],
            line_start=v["line_start"],
            line_end=v["line_end"],
            score_impact=v["score_impact"],
            rpm_impact=v["rpm_impact"],
            breaks_at_users=v["breaks_at_users"],
        )
        for v in violations_raw
    ]

    score = Score(**score_raw) if score_raw else Score(overall=100)

    cmd = ProcessStageCommand(job_id=UUID(job_id), stage="guide_gen")

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
            return guide

    try:
        guide = run_async(_run())
        prev_result["enterprise_guide"] = guide
        return prev_result
    except Exception as exc:
        logger.error("task_guide_gen_failed", job_id=job_id, error=str(exc))
        raise self.retry(exc=exc)
