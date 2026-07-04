import asyncio
import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from app.application.analysis.commands import (
    DeleteJobCommand,
    ProcessStageCommand,
    StartAnalysisCommand,
)
from app.application.analysis.queries import (
    DismissFindingsCommand,
    GetFindingsSummaryQuery,
    GetJobStatusQuery,
    GetReportQuery,
    ListFindingsQuery,
    ListJobsQuery,
)
from app.core.config import get_settings
from app.core.constants import JobStatus, Severity
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile
from app.domain.contracts.scorer import AbstractScorer, Violation
from app.domain.contracts.storage import AbstractStorage
from app.domain.entities.analysis_metadata import AnalysisMetadata
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
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.git.repository_fetcher import RepositoryFetcher
from app.infrastructure.messaging.producer import EventProducer
from app.infrastructure.parsers.base import ChainedParser
from app.workers.dead_code.detector import DeadCodeDetector, DeadCodeFinding
from app.workers.devops.analyzer import DevopsAnalyzer
from app.workers.devops.models import DevOpsFinding
from app.workers.enterprise_guide import EnterpriseGuideGenerator
from app.workers.errors.scanner import ErrorFinding, ErrorScanner
from app.workers.maintainability.detector import MaintainabilityDetector
from app.workers.maintainability.models import MaintainabilityFinding
from app.workers.perf.load_sim import ProductionSimulator
from app.workers.perf.rpm_calculator import PerformanceMetrics, RPMCalculator
from app.workers.reliability.detector import ReliabilityDetector
from app.workers.reliability.models import ReliabilityFinding

logger = get_logger(__name__)


async def handle_start_analysis(
    cmd: StartAnalysisCommand,
    uow: UnitOfWork,
    producer: EventProducer | None = None,
) -> UUID:
    job_id = uuid4()
    settings = get_settings()

    await uow.jobs.create(
        {
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
        }
    )

    if producer:
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
) -> dict[str, object]:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    await uow.jobs.update_status(
        cmd.job_id,
        JobStatus.CLONING,
        progress_pct=10,
        progress_message="Cloning repository...",
    )

    await producer.publish(
        AnalysisProgressed(
            job_id=cmd.job_id,
            status=JobStatus.CLONING,
            progress_pct=10,
        )
    )

    token = (
        get_settings().git.token.get_secret_value() if get_settings().git.token else ""
    )
    repo_path = await fetcher.clone(
        clone_url=cast(str, job["repo_url"]),
        branch=cast(str, job["branch"]),
        depth=1,
        github_token=token,
    )
    languages = await fetcher.detect_languages(repo_path)
    files = await fetcher.get_source_files(repo_path)
    loc = await fetcher.count_loc(repo_path)

    from app.infrastructure.detection.detector import FrameworkDetector

    detector = FrameworkDetector()
    detection = await detector.detect(repo_path)

    await uow.jobs.update_status(
        cmd.job_id,
        JobStatus.CLONING,
        progress_pct=10,
        progress_message=f"Found {len(files)} files across {len(languages)} languages",
        total_files=len(files),
        total_lines=loc,
    )

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


async def _push_progress(job_id: UUID, status: str, pct: int, message: str) -> None:
    from sqlalchemy import update

    from app.infrastructure.db.models.analysis_job import AnalysisJobModel
    from app.infrastructure.db.session import async_session_factory

    async with async_session_factory() as session:
        stmt = (
            update(AnalysisJobModel)
            .where(AnalysisJobModel.id == job_id)
            .values(status=status, progress_pct=pct, progress_message=message)
        )
        await session.execute(stmt)
        await session.commit()


async def handle_stage_parse(
    cmd: ProcessStageCommand,
    parser: ChainedParser,
    uow: UnitOfWork,
    producer: EventProducer,
    repo_path: str,
    files: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[ParsedFile]]:
    parsed: list[ParsedFile] = []
    errors = 0
    total = len(files)
    for i, f in enumerate(files):
        try:
            pf = await parser.parse(cast(str, f["path"]), cast(str, f["content"]))
            parsed.append(pf)
        except Exception:
            errors += 1
            logger.warning("parse_failed", path=f["path"], job_id=str(cmd.job_id))

        if (i + 1) % 5 == 0 or i == total - 1:
            pct = 25 + int(35 * (i + 1) / total)
            await _push_progress(
                cmd.job_id,
                JobStatus.PARSING,
                pct,
                f"Parsing files... ({i + 1}/{total})",
            )

    if errors:
        logger.warning(
            "parse_errors",
            count=errors,
            total=len(files),
            job_id=str(cmd.job_id),
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

    await _push_progress(
        cmd.job_id,
        JobStatus.PARSING,
        60,
        f"Parsed {len(parsed)} files ({errors} errors)"
        if errors
        else f"Parsed {len(parsed)} files",
    )

    return metadata, parsed


async def handle_stage_rules(
    cmd: ProcessStageCommand,
    registry: RuleRegistry,
    uow: UnitOfWork,
    producer: EventProducer,
    parsed_files: list[ParsedFile],
) -> tuple[list[dict[str, object]], list[RuleViolation]]:
    violations: list[RuleViolation] = []
    total = len(parsed_files)
    for i, pf in enumerate(parsed_files):
        ast_data = pf.ast_data
        ast_data["functions"] = [asdict(f) for f in pf.functions]
        ast_data["classes"] = [asdict(c) for c in pf.classes]
        ast_data["imports"] = [asdict(i) for i in pf.imports]
        ast_data["routes"] = [asdict(r) for r in pf.routes]

        applicable = registry.filter_for_file(pf.path, pf.language)
        for rule in applicable:
            try:
                rule_violations = await rule.analyze(
                    pf.path,
                    pf.content,
                    ast_data,
                )
                violations.extend(rule_violations)
            except Exception:
                logger.warning(
                    "rule_failed",
                    rule_id=rule.rule_id,
                    file=pf.path,
                    job_id=str(cmd.job_id),
                )

        if (i + 1) % 5 == 0 or i == total - 1:
            await _push_progress(
                cmd.job_id,
                JobStatus.RULES,
                50 + int(10 * (i + 1) / total),
                f"Analyzing {pf.path.split('/')[-1]}... ({i + 1}/{total})",
            )

    severity_counts = dict.fromkeys(Severity, 0)
    for v in violations:
        if v.severity in severity_counts:
            severity_counts[v.severity] += 1

    await uow.jobs.update_status(
        cmd.job_id,
        JobStatus.RULES,
        progress_pct=60,
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

    return cast(
        tuple[list[dict[str, object]], list[RuleViolation]], (summary, violations)
    )


def _dedup_violations(violations: list[RuleViolation]) -> list[RuleViolation]:
    """Remove duplicate violations based on (rule_id, file_path, line_start, line_end).

    Within a single pipeline run each rule fires once, so in-practice duplicates
    are rare.  This is a defensive guard that also makes re-runs safer.
    """
    seen: set[tuple[str, str, int, int]] = set()
    deduped: list[RuleViolation] = []
    for v in violations:
        key = (v.rule_id, v.file_path or "", v.line_start or 0, v.line_end or 0)
        if key not in seen:
            seen.add(key)
            deduped.append(v)
    return deduped


async def handle_save_findings(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    violations: list[RuleViolation],
    job: dict[str, object],
) -> list[Finding]:
    violations = _dedup_violations(violations)

    findings = [
        Finding(
            job_id=cmd.job_id,
            repo_id=cast(UUID, job["repo_id"]),
            workspace_id=cast(UUID, job["workspace_id"]),
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
    dead_code_results: list[DeadCodeFinding] | None = None,
    error_results: list[ErrorFinding] | None = None,
    reliability_results: list[ReliabilityFinding] | None = None,
    devops_results: list[DevOpsFinding] | None = None,
    maintainability_results: list[MaintainabilityFinding] | None = None,
    perf_metrics: PerformanceMetrics | None = None,
    simulation_results: list[dict[str, object]] | None = None,
    engine_statuses: dict[str, str] | None = None,
) -> Score:
    scorer_violations: list[Violation] = [
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

    # Dead code findings → maintainability violations (medium severity)
    if dead_code_results:
        for d in dead_code_results:
            scorer_violations.append(
                Violation(
                    rule_id=f"DEAD-{d.code_type.upper()}",
                    category="maintainability",
                    severity="medium",
                    title=f"Dead code: {d.name}",
                    description=f"Unused {d.code_type}: {d.name}",
                    file_path=d.file_path,
                    line_start=d.line_start,
                    line_end=d.line_end,
                )
            )

    # Error scanner findings → reliability violations
    if error_results:
        for e in error_results:
            scorer_violations.append(
                Violation(
                    rule_id=f"ERR-{e.error_type.upper()}",
                    category="reliability",
                    severity=e.severity,
                    title=e.title,
                    description=e.description,
                    file_path=e.file_path,
                    line_start=e.line_start,
                    line_end=e.line_end,
                    code_snippet=e.code_snippet or "",
                    recommendation=e.recommendation or "",
                )
            )

    # Dedicated reliability detector findings
    if reliability_results:
        for r in reliability_results:
            scorer_violations.append(
                Violation(
                    rule_id=f"REL-{r.reliability_type.upper()}",
                    category="reliability",
                    severity=r.severity,
                    title=r.title,
                    description=r.description,
                    file_path=r.file_path,
                    line_start=r.line_start,
                    line_end=r.line_end,
                    code_snippet=r.code_snippet or "",
                    recommendation=r.recommendation or "",
                )
            )

    # DevOps engine findings
    if devops_results:
        for devops_item in devops_results:
            scorer_violations.append(
                Violation(
                    rule_id=f"DEVOPS-{devops_item.devops_type.upper()}",
                    category="devops",
                    severity=devops_item.severity,
                    title=devops_item.title,
                    description=devops_item.description,
                    file_path=devops_item.file_path,
                    line_start=devops_item.line_start,
                    line_end=devops_item.line_end,
                    code_snippet=devops_item.code_snippet or "",
                    recommendation=devops_item.recommendation or "",
                )
            )

    # Maintainability engine findings
    if maintainability_results:
        for m in maintainability_results:
            scorer_violations.append(
                Violation(
                    rule_id=f"MAINT-{m.maintainability_type.upper()}",
                    category="maintainability",
                    severity=m.severity,
                    title=m.title,
                    description=m.description,
                    file_path=m.file_path,
                    line_start=m.line_start,
                    line_end=m.line_end,
                    code_snippet=m.code_snippet or "",
                    recommendation=m.recommendation or "",
                )
            )

    # Build capacity metrics from perf + simulation data
    from app.domain.contracts.scorer import CapacityMetrics

    capacity: CapacityMetrics | None = None
    if perf_metrics is not None or (simulation_results and len(simulation_results) > 0):
        sim_status: str | None = None
        bottlenecks: list[str] = list(perf_metrics.bottlenecks) if perf_metrics else []
        if simulation_results:
            for sr in simulation_results:
                s = cast(str, sr.get("status", ""))
                bottlenecks.extend(cast(list[str], sr.get("bottlenecks", [])))
                if s == "failing":
                    sim_status = "failing"
                elif s == "degraded" and sim_status != "failing":
                    sim_status = "degraded"
                elif s == "stable" and sim_status is None:
                    sim_status = "stable"

        capacity = CapacityMetrics(
            has_data=True,
            simulation_status=sim_status,
            breaks_at_users=perf_metrics.breaks_at_concurrent_users
            if perf_metrics
            else None,
            overall_rpm=perf_metrics.overall_rpm if perf_metrics else None,
            bottlenecks=bottlenecks,
        )

    score = scorer.calculate(
        scorer_violations,
        capacity=capacity,
        engine_statuses=engine_statuses,
        total_files=cmd.total_files,
    )
    return score


async def handle_stage_finalize(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    producer: EventProducer,
    storage: AbstractStorage,
    job: dict[str, object],
    score: Score,
    findings: list[Finding],
    languages: list[str],
    total_files: int,
    total_lines: int,
    duration_seconds: int,
) -> Report:
    get_settings()

    report = Report(
        job_id=cmd.job_id,
        repo_id=cast(UUID, job["repo_id"]),
        workspace_id=cast(UUID, job["workspace_id"]),
        branch=cast(str, job["branch"]),
        languages_detected=languages,
        total_files_analyzed=total_files,
        total_lines_of_code=total_lines,
        scores=score,
        findings=findings,
        duration_seconds=duration_seconds,
    )

    report_json = json.dumps(
        report.to_dict(),
        indent=2,
        default=str,
    ).encode("utf-8")

    s3_key = f"reports/{job['workspace_id']}/{cmd.job_id}/report.json"
    try:
        await storage.upload(s3_key, report_json)
        report.s3_key = s3_key
    except Exception:
        logger.warning("s3_upload_failed", key=s3_key, job_id=str(cmd.job_id))

    await uow.reports.save(report)

    await uow.score_history.save(
        {
            "time": datetime.now(UTC),
            "repo_id": job["repo_id"],
            "workspace_id": job["workspace_id"],
            "overall_score": score.overall if score.overall is not None else 0,
            "performance_score": score.performance,
            "security_score": score.security,
            "reliability_score": score.reliability,
            "maintainability_score": score.maintainability,
            "devops_score": score.devops,
            "findings_count": len(findings),
            "job_id": cmd.job_id,
        }
    )

    severity_counts = dict.fromkeys(Severity, 0)
    for f in findings:
        if f.severity in severity_counts:
            severity_counts[f.severity] += 1

    await uow.jobs.update_status(
        cmd.job_id,
        JobStatus.COMPLETED,
        progress_pct=100,
        progress_message="Analysis complete",
        overall_score=score.overall,
        blocked_by=score.blocked_by,
        engine_statuses=score.engine_statuses,
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
        completed_at=datetime.now(UTC).replace(tzinfo=None),
    )

    await producer.publish(
        AnalysisCompleted(
            job_id=cmd.job_id,
            repo_id=cast(UUID, job["repo_id"]),
            workspace_id=cast(UUID, job["workspace_id"]),
            overall_score=score.overall,
            findings_count=len(findings),
            duration_seconds=duration_seconds,
            engine_statuses=score.engine_statuses,
            blocked_by=score.blocked_by,
        )
    )

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
            job_id,
            JobStatus.FAILED,
            progress_pct=0,
            progress_message=f"Failed at stage: {stage}",
            error_message=error_message,
        )

    try:
        await asyncio.wait_for(
            producer.publish(
                AnalysisFailed(
                    job_id=job_id,
                    repo_id=cast(UUID, job["repo_id"]) if job else UUID(int=0),
                    error_message=error_message,
                    stage=stage,
                )
            ),
            timeout=5,
        )
    except Exception:
        logger.warning("analysis_failed_publish_failed", job_id=str(job_id))

    logger.error(
        "analysis_failed",
        job_id=str(job_id),
        stage=stage,
        error=error_message,
    )


async def handle_stage_dead_code(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    producer: EventProducer,
    parsed_files: list[ParsedFile],
) -> list[DeadCodeFinding]:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    detector = DeadCodeDetector(parsed_files)
    dead_code_results = await detector.detect_all()

    if dead_code_results:
        entries = [r.to_dict() for r in dead_code_results]
        for e in entries:
            e["job_id"] = cmd.job_id
            e["repo_id"] = job["repo_id"]
            e["workspace_id"] = job["workspace_id"]
        await uow.dead_code.save_many(entries)
        logger.info(
            "dead_code_saved",
            count=len(entries),
            job_id=str(cmd.job_id),
        )

    await uow.jobs.update_status(
        cmd.job_id,
        JobStatus.DEAD_CODE,
        progress_pct=83,
        progress_message=f"Found {len(dead_code_results)} dead code instances",
    )

    return dead_code_results


async def handle_stage_errors(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    producer: EventProducer,
    parsed_files: list[ParsedFile],
) -> list[ErrorFinding]:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    scanner = ErrorScanner(parsed_files)
    error_results = await scanner.scan_all()

    if error_results:
        entries = [r.to_dict() for r in error_results]
        for e in entries:
            e["job_id"] = cmd.job_id
            e["repo_id"] = job["repo_id"]
            e["workspace_id"] = job["workspace_id"]
        await uow.error_findings.save_many(entries)
        logger.info(
            "errors_saved",
            count=len(entries),
            job_id=str(cmd.job_id),
        )

    await uow.jobs.update_status(
        cmd.job_id,
        JobStatus.ERRORS,
        progress_pct=86,
        progress_message=f"Found {len(error_results)} error patterns",
    )

    return error_results


async def handle_stage_reliability(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    producer: EventProducer,
    parsed_files: list[ParsedFile],
) -> list[ReliabilityFinding]:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    detector = ReliabilityDetector(parsed_files)
    reliability_results = await detector.scan_all()

    if reliability_results:
        entries = [r.to_dict() for r in reliability_results]
        for e in entries:
            e["job_id"] = cmd.job_id
            e["repo_id"] = job["repo_id"]
            e["workspace_id"] = job["workspace_id"]
        await uow.reliability_findings.save_many(entries)
        logger.info(
            "reliability_findings_saved",
            count=len(entries),
            job_id=str(cmd.job_id),
        )

    await uow.jobs.update_status(
        cmd.job_id,
        "reliability",
        progress_pct=84,
        progress_message=f"Found {len(reliability_results)} reliability issues",
    )

    return reliability_results


async def handle_stage_maintainability(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    producer: EventProducer,
    parsed_files: list[ParsedFile],
) -> list[MaintainabilityFinding]:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    detector = MaintainabilityDetector(parsed_files)
    maintainability_results = await detector.scan_all()
    metrics = detector.compute_metrics(maintainability_results)

    if maintainability_results:
        entries = [r.to_dict() for r in maintainability_results]
        for e in entries:
            e["job_id"] = cmd.job_id
            e["repo_id"] = job["repo_id"]
            e["workspace_id"] = job["workspace_id"]
            e["metrics"] = metrics.to_dict()
        await uow.maintainability_findings.save_many(entries)
        logger.info(
            "maintainability_findings_saved",
            count=len(entries),
            job_id=str(cmd.job_id),
        )

    await uow.jobs.update_status(
        cmd.job_id,
        "maintainability",
        progress_pct=82,
        progress_message=f"Found {len(maintainability_results)} maintainability issues",
    )

    return maintainability_results


async def handle_stage_devops(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    producer: EventProducer,
    parsed_files: list[ParsedFile],
) -> list[DevOpsFinding]:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    analyzer = DevopsAnalyzer(parsed_files)
    devops_results = await analyzer.scan_all()

    if devops_results:
        entries = [r.to_dict() for r in devops_results]
        for e in entries:
            e["job_id"] = cmd.job_id
            e["repo_id"] = job["repo_id"]
            e["workspace_id"] = job["workspace_id"]
        await uow.devops_findings.save_many(entries)
        logger.info(
            "devops_findings_saved",
            count=len(entries),
            job_id=str(cmd.job_id),
        )

    await uow.jobs.update_status(
        cmd.job_id,
        "devops",
        progress_pct=86,
        progress_message=f"Found {len(devops_results)} DevOps issues",
    )

    return devops_results


async def handle_stage_perf(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    producer: EventProducer,
    parsed_files: list[ParsedFile],
) -> PerformanceMetrics | None:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    try:
        calculator = RPMCalculator(parsed_files)
        perf_metrics = await calculator.calculate()

        if perf_metrics.endpoints:
            entries = [em.to_dict() for em in perf_metrics.endpoints]
            for e in entries:
                e["job_id"] = cmd.job_id
                e["repo_id"] = job["repo_id"]
                e["workspace_id"] = job["workspace_id"]
            await uow.performance_metrics.save_many(entries)
            logger.info(
                "perf_metrics_saved",
                count=len(entries),
                job_id=str(cmd.job_id),
            )

        await uow.jobs.update_status(
            cmd.job_id,
            JobStatus.PERF,
            progress_pct=90,
            progress_message=f"Estimated RPM: {perf_metrics.overall_rpm}, "
            f"breaks at {perf_metrics.breaks_at_concurrent_users} users",
        )

        return perf_metrics
    except Exception:
        logger.warning("perf_analysis_failed", job_id=str(cmd.job_id))
        await uow.jobs.update_status(
            cmd.job_id,
            JobStatus.PERF,
            progress_pct=90,
            progress_message="Performance analysis skipped due to error",
        )
        return None


async def handle_stage_simulation(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    producer: EventProducer,
    perf_metrics: PerformanceMetrics | None,
) -> list[dict[str, object]]:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    if not perf_metrics:
        await uow.jobs.update_status(
            cmd.job_id,
            JobStatus.SIMULATION,
            progress_pct=93,
            progress_message="Simulation skipped (no performance data)",
        )
        return []

    try:
        simulator = ProductionSimulator()
        sim_results = await simulator.simulate(perf_metrics)

        if sim_results:
            entries = [r.to_dict() for r in sim_results]
            for e in entries:
                e["job_id"] = cmd.job_id
                e["repo_id"] = job["repo_id"]
                e["workspace_id"] = job["workspace_id"]
            await uow.simulation_results.save_many(entries)
            statuses = [s.status for s in sim_results]
            logger.info(
                "simulation_complete",
                job_id=str(cmd.job_id),
                statuses=statuses,
            )

        await uow.jobs.update_status(
            cmd.job_id,
            JobStatus.SIMULATION,
            progress_pct=93,
            progress_message=f"Simulated {len(sim_results)} load levels",
        )

        return [r.to_dict() for r in sim_results]
    except Exception:
        logger.warning("simulation_failed", job_id=str(cmd.job_id))
        return []


async def handle_stage_guide_gen(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    producer: EventProducer,
    violations: list[RuleViolation],
    score: Score,
    perf_metrics: PerformanceMetrics | None = None,
    simulation_results: list[dict[str, object]] | None = None,
    dead_code_results: list[DeadCodeFinding] | None = None,
    error_results: list[ErrorFinding] | None = None,
    reliability_results: list[ReliabilityFinding] | None = None,
    devops_results: list[DevOpsFinding] | None = None,
    maintainability_results: list[MaintainabilityFinding] | None = None,
) -> dict[str, object] | None:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    try:
        from app.workers.perf.load_sim import SimulationResult as SimRes

        sim_objects: list[SimRes] = []
        if simulation_results:
            sim_objects = [SimRes(**s) for s in simulation_results]  # type: ignore[arg-type]

        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(
            findings=violations,
            scores=score,
            perf_metrics=perf_metrics,
            simulation=sim_objects,
            dead_code=dead_code_results,
            errors=error_results,
            reliability=reliability_results,
            devops=devops_results,
            maintainability=maintainability_results,
        )

        guide_dict = guide.to_dict()
        guide_dict["job_id"] = cmd.job_id
        guide_dict["repo_id"] = job["repo_id"]
        guide_dict["workspace_id"] = job["workspace_id"]

        await uow.enterprise_guides.save(guide_dict)
        logger.info("enterprise_guide_saved", job_id=str(cmd.job_id))

        await uow.jobs.update_status(
            cmd.job_id,
            JobStatus.GUIDE_GEN,
            progress_pct=97,
            progress_message="Enterprise guide generated",
        )

        return guide_dict
    except Exception as exc:
        logger.warning(
            "guide_gen_failed",
            job_id=str(cmd.job_id),
            error=str(exc),
        )
        return None


async def handle_stage_ai_enrich(
    cmd: ProcessStageCommand,
    uow: UnitOfWork,
    findings: list[Finding],
    score: Score | None = None,
    languages: list[str] | None = None,
    frameworks: list[str] | None = None,
) -> dict[str, object] | None:
    from app.infrastructure.ai.enrichment_client import AiEnrichmentClient

    job_id = cmd.job_id
    job = await uow.jobs.get_by_id(job_id)
    if not job:
        raise NotFoundError(f"Job {job_id} not found")

    finding_dicts = []
    for f in findings:
        finding_dicts.append(
            {
                "title": f.title,
                "category": str(f.category),
                "severity": str(f.severity),
                "description": f.description or "",
                "recommendation": f.recommendation or "",
                "file_path": f.file_path or "",
                "line_start": f.line_start,
                "line_end": f.line_end,
                "code_snippet": f.code_snippet or "",
            }
        )

    if not finding_dicts:
        await uow.jobs.update_status(
            job_id,
            JobStatus.AI_ENRICH,
            progress_pct=98,
            progress_message="AI enrichment skipped (no findings)",
        )
        return {"findings": [], "ai_executive_summary": ""}

    client = AiEnrichmentClient()
    result = await client.enrich_findings(
        findings=cast(list[dict[str, object]], finding_dicts),
        overall_score=score.overall if score else None,
        tier=str(score.tier) if score and score.tier else None,
        languages=languages,
        frameworks=frameworks,
    )

    if not result:
        logger.info("ai_enrichment_unavailable", job_id=str(job_id))
        await uow.jobs.update_status(
            job_id,
            JobStatus.AI_ENRICH,
            progress_pct=98,
            progress_message="AI enrichment skipped (service unavailable)",
        )
        return None

    enriched_findings_map: dict[str, dict[str, object]] = {}
    enrich_data = result.get("findings", [])
    if not isinstance(enrich_data, list):
        raise RuntimeError(
            f"Expected enrich_data to be a list, got {type(enrich_data).__name__}"
        )
    for item in enrich_data:
        title = item.get("title", "")
        file_path = item.get("file_path", "")
        key = f"{title}|{file_path}"
        enriched_findings_map[key] = item

    updated_count = 0
    for finding in findings:
        key = f"{finding.title}|{finding.file_path}"
        enriched = enriched_findings_map.get(key)
        if enriched and enriched.get("is_ai_enriched"):
            await uow.findings.update_ai_fields(
                finding_id=finding.id,
                is_ai_enriched=True,
                ai_explanation=str(enriched.get("ai_explanation", "")),
            )
            updated_count += 1

    ai_executive_summary = str(result.get("ai_executive_summary", ""))
    if ai_executive_summary:
        guide = await uow.enterprise_guides.get_by_job(job_id)
        if guide:
            guide["ai_executive_summary"] = ai_executive_summary
            await uow.enterprise_guides.save(guide)

    await uow.jobs.update_status(
        job_id,
        JobStatus.AI_ENRICH,
        progress_pct=98,
        progress_message=f"AI enrichment complete ({updated_count} findings enriched)",
    )

    logger.info(
        "ai_enrichment_complete",
        job_id=str(job_id),
        enriched=updated_count,
        total=len(findings),
    )
    return result


async def get_job_status(
    query: GetJobStatusQuery,
    uow: UnitOfWork,
) -> dict[str, object] | None:
    return await uow.jobs.get_by_id(query.job_id)


async def list_findings(
    query: ListFindingsQuery,
    uow: UnitOfWork,
) -> tuple[list[Finding], int]:
    return await uow.findings.get_by_job(
        query.job_id,
        category=query.category,
        severity=query.severity,
        include_dismissed=query.include_dismissed,
        limit=query.limit,
        offset=query.offset,
    )


async def dismiss_findings(
    command: DismissFindingsCommand,
    uow: UnitOfWork,
) -> int:
    return await uow.findings.dismiss_many(command.finding_ids)


async def get_findings_summary(
    query: GetFindingsSummaryQuery,
    uow: UnitOfWork,
) -> dict[str, object]:
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
    if query.report_id:
        return await uow.reports.get_by_job(query.report_id)
    if query.job_id:
        return await uow.reports.get_by_job(query.job_id)
    return None


async def list_jobs(
    query: ListJobsQuery,
    uow: UnitOfWork,
) -> dict[str, object]:
    if query.repo_id:
        jobs, total = await uow.jobs.list_by_repo(
            query.repo_id,
            limit=query.limit,
            offset=query.offset,
        )
        return {"jobs": jobs, "total": total}
    if query.workspace_id:
        jobs, total = await uow.jobs.list_by_workspace(
            query.workspace_id,
            limit=query.limit,
            offset=query.offset,
        )
        return {"jobs": jobs, "total": total}
    return {"jobs": [], "total": 0}


async def handle_delete_job(
    cmd: DeleteJobCommand,
    uow: UnitOfWork,
    storage: AbstractStorage | None = None,
) -> dict[str, object]:
    """Permanently delete a job and all its data."""
    job = await uow.jobs.hard_delete(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    # Clean up S3 artifacts for this job
    if storage:
        s3_prefix = f"reports/{cmd.workspace_id}/{cmd.job_id}"
        try:
            s3_keys = await storage.list_keys(s3_prefix)
            for key in s3_keys:
                await storage.delete(key)
        except Exception:
            logger.warning(
                "s3_cleanup_failed", job_id=str(cmd.job_id), prefix=s3_prefix
            )

    logger.info("job_deleted", job_id=str(cmd.job_id))
    return job


async def get_dead_code(
    job_id: UUID,
    uow: UnitOfWork,
) -> list[dict[str, object]]:
    return await uow.dead_code.get_by_job(job_id)


async def get_error_findings(
    job_id: UUID,
    uow: UnitOfWork,
) -> list[dict[str, object]]:
    return await uow.error_findings.get_by_job(job_id)


async def get_performance_metrics(
    job_id: UUID,
    uow: UnitOfWork,
) -> list[dict[str, object]]:
    return await uow.performance_metrics.get_by_job(job_id)


async def get_simulation_results(
    job_id: UUID,
    uow: UnitOfWork,
) -> list[dict[str, object]]:
    return await uow.simulation_results.get_by_job(job_id)


async def get_enterprise_guide(
    job_id: UUID,
    uow: UnitOfWork,
) -> dict[str, object] | None:
    return await uow.enterprise_guides.get_by_job(job_id)


async def handle_save_analysis_metadata(
    job_id: UUID,
    parsed_files_metadata: list[dict[str, object]],
    languages: list[str],
    frameworks: list[str],
    uow: UnitOfWork,
) -> None:
    class_count = 0
    function_count = 0
    endpoint_count = 0
    for meta in parsed_files_metadata:
        class_count += cast(int, meta.get("classes", 0))
        function_count += cast(int, meta.get("functions", 0))
        endpoint_count += cast(int, meta.get("routes", 0))

    metadata = AnalysisMetadata(
        job_id=job_id,
        class_count=class_count,
        function_count=function_count,
        endpoint_count=endpoint_count,
        languages=list(dict.fromkeys(languages)),
        frameworks=list(dict.fromkeys(frameworks)),
    )
    await uow.analysis_metadata.save(metadata)
    logger.info(
        "analysis_metadata_saved",
        job_id=str(job_id),
        classes=class_count,
        functions=function_count,
        endpoints=endpoint_count,
    )


async def get_analysis_metadata(
    job_id: UUID,
    uow: UnitOfWork,
) -> AnalysisMetadata | None:
    return await uow.analysis_metadata.get_by_job(job_id)
