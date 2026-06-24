import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.application.analysis.commands import (
    ProcessStageCommand,
    StartAnalysisCommand,
)
from app.application.analysis.queries import (
    GetFindingsSummaryQuery,
    GetJobStatusQuery,
    GetReportQuery,
    ListFindingsQuery,
    ListJobsQuery,
)
from app.core.config import get_settings
from app.core.constants import Category, JobStatus, Severity
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile
from app.domain.contracts.scorer import AbstractScorer, Violation
from app.domain.contracts.storage import AbstractStorage
from app.domain.entities.finding import Finding
from app.domain.entities.report import Report
from app.domain.entities.score import Score
from app.domain.events import (
    AnalysisCompleted,
    AnalysisFailed,
    AnalysisProgressed,
    AnalysisRequested,
)
from app.domain.rules.base import RuleViolation
from app.domain.rules.registry import RuleRegistry
from app.infrastructure.cache.redis import RedisCache
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.git.repository_fetcher import RepositoryFetcher
from app.infrastructure.messaging.producer import EventProducer
from app.infrastructure.parsers.base import ChainedParser

logger = get_logger(__name__)


async def handle_start_analysis(
    cmd: StartAnalysisCommand,
    uow: UnitOfWork,
    producer: EventProducer,
) -> UUID:
    job_id = uuid4()
    settings = get_settings()

    await uow.jobs.create({
        "id": job_id,
        "repo_id": cmd.repo_id,
        "workspace_id": cmd.workspace_id,
        "triggered_by": cmd.triggered_by,
        "trigger_type": cmd.trigger_type,
        "repo_url": cmd.repo_url,
        "branch": cmd.branch,
        "deep_scan": cmd.deep_scan,
        "simulate_users": cmd.simulate_users or settings.analysis.simulate_users,
        "status": JobStatus.QUEUED,
        "progress_pct": 0,
        "progress_message": "Analysis queued",
        "total_findings": 0,
    })

    event = AnalysisRequested(
        job_id=job_id,
        repo_id=cmd.repo_id,
        workspace_id=cmd.workspace_id,
        triggered_by=cmd.triggered_by,
        trigger_type=cmd.trigger_type,
        branch=cmd.branch,
        deep_scan=cmd.deep_scan,
    )
    await producer.publish(event)

    logger.info("analysis_started", job_id=str(job_id), repo_id=str(cmd.repo_id))
    return job_id


async def handle_stage_clone(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    fetcher: RepositoryFetcher,
    producer: EventProducer,
) -> dict:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    await uow.jobs.update_status(
        cmd.job_id, JobStatus.CLONING, progress_pct=10,
        progress_message="Cloning repository...",
    )
    await producer.publish(AnalysisProgressed(
        job_id=cmd.job_id, status=JobStatus.CLONING, progress_pct=10,
    ))

    repo_path = await fetcher.clone(
        clone_url=job["repo_url"],
        branch=job["branch"],
        depth=1,
    )
    languages = await fetcher.detect_languages(repo_path)
    files = await fetcher.get_source_files(repo_path)
    loc = await fetcher.count_loc(repo_path)

    from app.infrastructure.detection.detector import FrameworkDetector

    detector = FrameworkDetector()
    detection = await detector.detect(repo_path)

    result = {
        "repo_path": repo_path,
        "languages": languages,
        "files": files,
        "total_lines": loc,
        "total_files": len(files),
        "job_id": str(cmd.job_id),
        "frameworks": [t.name for t in detection.frameworks],
        "databases": [t.name for t in detection.databases],
        "tools": [t.name for t in detection.tools],
        "infra": [t.name for t in detection.infra],
        "detection_result": detection.to_dict(),
    }

    logger.info("repo_cloned", job_id=str(cmd.job_id), languages=languages)
    return result


async def handle_stage_parse(
    cmd: ProcessStageCommand,
    parser: ChainedParser,
    uow: UnitOfWork,
    producer: EventProducer,
    repo_path: str,
    files: list[dict],
) -> list[dict]:
    await uow.jobs.update_status(
        cmd.job_id, JobStatus.PARSING, progress_pct=25,
        progress_message=f"Parsing {len(files)} files...",
    )
    await producer.publish(AnalysisProgressed(
        job_id=cmd.job_id, status=JobStatus.PARSING, progress_pct=25,
    ))

    parsed: list[ParsedFile] = []
    errors = 0
    for f in files:
        try:
            pf = await parser.parse(f["path"], f["content"])
            parsed.append(pf)
        except Exception:
            errors += 1
            logger.warning("parse_failed", path=f["path"], job_id=str(cmd.job_id))

    if errors:
        logger.warning(
            "parse_errors", count=errors, total=len(files), job_id=str(cmd.job_id),
        )

    metadata = [
        {
            "path": p.path,
            "language": p.language,
            "lines": p.lines_count,
            "functions": len(p.functions),
            "classes": len(p.classes),
            "routes": len(p.routes),
            "imports": len(p.imports),
            "has_errors": len(p.errors) > 0,
        }
        for p in parsed
    ]

    return metadata


async def handle_stage_rules(
    cmd: ProcessStageCommand,
    registry: RuleRegistry,
    uow: UnitOfWork,
    producer: EventProducer,
    parsed_files: list[ParsedFile],
) -> list[dict]:
    await uow.jobs.update_status(
        cmd.job_id, JobStatus.RULES, progress_pct=50,
        progress_message="Running domain rules...",
    )
    await producer.publish(AnalysisProgressed(
        job_id=cmd.job_id, status=JobStatus.RULES, progress_pct=50,
    ))

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
                rule_violations = await rule.analyze(
                    pf.path, pf.content, ast_data,
                )
                violations.extend(rule_violations)
            except Exception:
                logger.warning(
                    "rule_failed", rule_id=rule.rule_id,
                    file=pf.path, job_id=str(cmd.job_id),
                )

    severity_counts = {s: 0 for s in Severity}
    for v in violations:
        if v.severity in severity_counts:
            severity_counts[v.severity] += 1

    await uow.jobs.update_status(
        cmd.job_id, JobStatus.RULES, progress_pct=60,
        progress_message=f"Found {len(violations)} issues",
        total_findings=len(violations),
        critical_count=severity_counts.get(Severity.CRITICAL, 0),
        high_count=severity_counts.get(Severity.HIGH, 0),
        medium_count=severity_counts.get(Severity.MEDIUM, 0),
        low_count=severity_counts.get(Severity.LOW, 0),
    )

    summary = [
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

    return summary


async def handle_save_findings(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    violations: list[RuleViolation],
    job: dict,
) -> list[Finding]:
    findings = [
        Finding(
            job_id=cmd.job_id,
            repo_id=job["repo_id"],
            workspace_id=job["workspace_id"],
            rule_id=v.rule_id,
            category=v.category,
            severity=v.severity,
            title=v.title,
            description=v.description,
            recommendation=v.recommendation,
            enterprise_pattern=v.enterprise_pattern,
            file_path=v.file_path,
            line_start=v.line_start,
            line_end=v.line_end,
            code_snippet=v.code_snippet,
            score_impact=v.score_impact,
            rpm_impact=v.rpm_impact,
            breaks_at_users=v.breaks_at_users,
        )
        for v in violations
    ]

    if findings:
        saved = await uow.findings.save_many(findings)
        logger.info("findings_saved", count=saved, job_id=str(cmd.job_id))

    return findings


async def handle_stage_score(
    cmd: ProcessStageCommand,
    scorer: AbstractScorer,
    uow: UnitOfWork,
    producer: EventProducer,
    violations: list[RuleViolation],
) -> Score:
    await uow.jobs.update_status(
        cmd.job_id, JobStatus.SCORING, progress_pct=85,
        progress_message="Calculating score...",
    )
    await producer.publish(AnalysisProgressed(
        job_id=cmd.job_id, status=JobStatus.SCORING, progress_pct=85,
    ))

    scorer_violations = [
        Violation(
            rule_id=v.rule_id,
            category=str(v.category),
            severity=str(v.severity),
            title=v.title,
            description=v.description,
            file_path=v.file_path,
            line_start=v.line_start,
            line_end=v.line_end,
            code_snippet=v.code_snippet,
            recommendation=v.recommendation,
            enterprise_pattern=v.enterprise_pattern,
            score_impact=v.score_impact,
            rpm_impact=v.rpm_impact,
            breaks_at_users=v.breaks_at_users,
        )
        for v in violations
    ]

    settings = get_settings()
    weights = {
        "performance": settings.scoring.performance_weight,
        "security": settings.scoring.security_weight,
        "reliability": settings.scoring.reliability_weight,
        "maintainability": settings.scoring.maintainability_weight,
        "devops": settings.scoring.devops_weight,
    }

    score = scorer.calculate(scorer_violations, weights=weights)
    return score


async def handle_stage_finalize(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    producer: EventProducer,
    storage: AbstractStorage,
    job: dict,
    score: Score,
    findings: list[Finding],
    languages: list[str],
    total_files: int,
    total_lines: int,
    duration_seconds: int,
) -> Report:
    settings = get_settings()

    report = Report(
        job_id=cmd.job_id,
        repo_id=job["repo_id"],
        workspace_id=job["workspace_id"],
        branch=job["branch"],
        languages_detected=languages,
        total_files_analyzed=total_files,
        total_lines_of_code=total_lines,
        scores=score,
        findings=findings,
        duration_seconds=duration_seconds,
    )

    report_json = json.dumps(
        report.to_dict(), indent=2, default=str,
    ).encode("utf-8")

    s3_key = (
        f"reports/{job['workspace_id']}/{cmd.job_id}/report.json"
    )
    try:
        await storage.upload(s3_key, report_json)
        report.s3_key = s3_key
    except Exception:
        logger.warning("s3_upload_failed", key=s3_key, job_id=str(cmd.job_id))

    await uow.reports.save(report)

    severity_counts = {s: 0 for s in Severity}
    for f in findings:
        if f.severity in severity_counts:
            severity_counts[f.severity] += 1

    await uow.jobs.update_status(
        cmd.job_id, JobStatus.COMPLETED, progress_pct=100,
        progress_message="Analysis complete",
        overall_score=score.overall,
        performance_score=score.performance,
        security_score=score.security,
        reliability_score=score.reliability,
        maintainability_score=score.maintainability,
        devops_score=score.devops,
        total_findings=len(findings),
        critical_count=severity_counts.get(Severity.CRITICAL, 0),
        high_count=severity_counts.get(Severity.HIGH, 0),
        medium_count=severity_counts.get(Severity.MEDIUM, 0),
        low_count=severity_counts.get(Severity.LOW, 0),
        duration_seconds=duration_seconds,
        completed_at=datetime.now(timezone.utc),
    )

    await producer.publish(AnalysisCompleted(
        job_id=cmd.job_id,
        repo_id=job["repo_id"],
        workspace_id=job["workspace_id"],
        overall_score=score.overall,
        findings_count=len(findings),
        duration_seconds=duration_seconds,
    ))

    logger.info(
        "analysis_completed",
        job_id=str(cmd.job_id),
        score=score.overall,
        findings=len(findings),
    )

    return report


async def handle_analysis_failure(
    job_id: UUID,
    stage: str,
    error_message: str,
    uow: UnitOfWork,
    producer: EventProducer,
) -> None:
    try:
        job = await uow.jobs.get_by_id(job_id)
    except Exception:
        job = None

    if job:
        await uow.jobs.update_status(
            job_id, JobStatus.FAILED, progress_pct=0,
            progress_message=f"Failed at stage: {stage}",
            error_message=error_message,
        )

    await producer.publish(AnalysisFailed(
        job_id=job_id,
        repo_id=job["repo_id"] if job else UUID(int=0),
        error_message=error_message,
        stage=stage,
    ))

    logger.error(
        "analysis_failed",
        job_id=str(job_id), stage=stage, error=error_message,
    )


async def get_job_status(
    query: GetJobStatusQuery,
    uow: UnitOfWork,
) -> dict | None:
    return await uow.jobs.get_by_id(query.job_id)


async def list_findings(
    query: ListFindingsQuery,
    uow: UnitOfWork,
) -> tuple[list[Finding], int]:
    return await uow.findings.get_by_job(
        query.job_id,
        category=query.category,
        severity=query.severity,
        limit=query.limit,
        offset=query.offset,
    )


async def get_findings_summary(
    query: GetFindingsSummaryQuery,
    uow: UnitOfWork,
) -> dict:
    by_severity = await uow.findings.count_by_severity(query.job_id)
    by_category = await uow.findings.count_by_category(query.job_id)
    return {
        "by_severity": by_severity,
        "by_category": by_category,
    }


async def get_report(
    query: GetReportQuery,
    uow: UnitOfWork,
) -> Report | None:
    return await uow.reports.get_by_job(query.job_id)


async def list_jobs(
    query: ListJobsQuery,
    uow: UnitOfWork,
) -> list[dict]:
    if query.repo_id:
        return await uow.jobs.list_by_repo(
            query.repo_id, limit=query.limit, offset=query.offset,
        )
    if query.workspace_id:
        return await uow.jobs.list_by_workspace(
            query.workspace_id, limit=query.limit, offset=query.offset,
        )
    return []
