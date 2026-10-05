import asyncio
import json
from collections.abc import Sequence
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
    GetJobStatisticsQuery,
    GetJobStatusQuery,
    GetReportQuery,
    ListFindingsQuery,
    ListJobsQuery,
)
from app.core.config import get_settings
from app.core.constants import (
    Category,
    EngineStateMap,
    EngineStatus,
    JobStatus,
    Severity,
)
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

# How much of a failure detail to keep on the job. The exception's own message is
# usually a sentence; anything past this is a driver's diagnostic that names
# internals without saying anything a person can act on.
_MAX_FAILURE_DETAIL = 400

# A traceback line that points at a source frame, e.g.
#   File "/srv/app/core/pipeline.py", line 214, in run_pipeline
_TRACEBACK_FRAME = 'File "'


def describe_failure(stage: str, error_message: str | None) -> str:
    """A failure message fit to store on the job and read back over the API.

    `error_message` arrives from three callers, and the pipeline one passes
    ``traceback.format_exc()``. The job row is served by ``GET /jobs/{id}``, so a
    traceback in this column put absolute server paths, internal module names and
    whatever the exception happened to embed -- a connection string, a URL with a
    token in it -- in front of anyone who could read the job. The engine column
    was already guarded for exactly this; the job column next to it was not.

    A traceback also tells the person reading it very little. It ends in the
    deepest internal frame, not the cause. What answers "why did this fail?" is
    the stage it failed in and the exception's own message, which is all this
    keeps.

    The traceback is not lost. ``run_full_analysis`` logs it with
    ``logger.exception("pipeline_aborted")`` before re-raising, so it reaches the
    logs on every path that produced one.
    """
    summary = f"{stage} failed"
    detail = _exception_detail(error_message)
    return f"{summary}: {detail}" if detail else summary


# The only keys from the AI service's `ai_summary_error` envelope that may be
# stored or served. Whitelist rather than blacklist: the envelope crosses a
# network boundary from a service that deploys independently, and a blacklist
# only protects against the leaks somebody already thought of. A field added to
# the envelope upstream is ignored here until somebody adds it deliberately.
_SUMMARY_ERROR_KEYS = ("code", "message", "suggested_action", "retry_after")


def _carried_across_regeneration(existing: dict[str, object]) -> dict[str, object]:
    """The AI summary fields a guide regeneration does not itself produce.

    `EnterpriseGuide.to_dict()` knows nothing about `ai_executive_summary` or
    `ai_summary_error`, so `handle_re_generate_guide` has to copy both across by
    hand. Skip either and `save()` hands `merge()` an instance with that column
    unset, which nulls the recorded value -- silently losing a summary the user
    paid for, and silently losing the reason one is missing.

    Both are returned together, and the error is checked with `is not None`
    rather than truthiness: `{}` is a real if degenerate reason to keep, and
    `None` is the only thing that means "no error". Treating the two the same is
    how the error would come back as `{}` on a guide that had none.
    """
    carried: dict[str, object] = {}
    summary = existing.get("ai_executive_summary")
    if summary:
        carried["ai_executive_summary"] = summary
    error = existing.get("ai_summary_error")
    if error is not None:
        carried["ai_summary_error"] = error
    return carried


def _readable_summary_error(raw: object) -> dict[str, object] | None:
    """Narrow the AI service's summary-error envelope to what is safe to serve.

    The AI service already builds this from four named fields on
    ``ClassifiedError`` rather than by copying the exception, so the provider
    name, the model and the verbatim provider response body are not in it to
    begin with. That is a real defence, but it is a defence in *that* service
    about *that* object; this is a second boundary, and the guide endpoint serves
    whatever lands in this column to browsers.

    Returns ``None`` -- "no reason was reported" -- rather than a synthetic one
    when the payload is unusable, because inventing a code here would put a
    confident-sounding wrong answer in the place where the truth is missing. The
    caller distinguishes the two.
    """
    if not isinstance(raw, dict):
        return None
    code = raw.get("code")
    message = raw.get("message")
    if not isinstance(code, str) or not code.strip():
        return None
    if not isinstance(message, str) or not message.strip():
        return None

    error: dict[str, object] = {"code": code, "message": message}

    action = raw.get("suggested_action")
    if isinstance(action, str) and action.strip():
        error["suggested_action"] = action

    # Omitted rather than stored as null, matching the envelope: a client cannot
    # tell "no hint" from "hint of zero", and a zero hint reads as "retry now".
    retry_after = raw.get("retry_after")
    if isinstance(retry_after, int | float) and not isinstance(retry_after, bool):
        error["retry_after"] = retry_after

    assert set(error).issubset(_SUMMARY_ERROR_KEYS)
    return error


def _exception_detail(error_message: str | None) -> str:
    """The part of a failure message worth serving, bounded and single-line."""
    if not error_message:
        return ""
    lines = [line.strip() for line in error_message.splitlines() if line.strip()]

    # A traceback is a run of `File "..."` frames with the `SomeError: detail`
    # line after the last one. Everything up to that point is machinery. A
    # message that is not a traceback has no frames and is used as it stands.
    last_frame = max(
        (i for i, line in enumerate(lines) if line.startswith(_TRACEBACK_FRAME)),
        default=None,
    )
    if last_frame is not None:
        tail = lines[last_frame + 1 :]
        if tail:
            lines = tail

    return " ".join(lines)[:_MAX_FAILURE_DETAIL].strip()


async def handle_start_analysis(
    cmd: StartAnalysisCommand, uow: UnitOfWork, producer: EventProducer | None = None
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
            "depth": cmd.depth,
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
        AnalysisProgressed(job_id=cmd.job_id, status=JobStatus.CLONING, progress_pct=10)
    )

    token = (
        get_settings().git.token.get_secret_value() if get_settings().git.token else ""
    )
    clone_depth = cast(int, job.get("depth", 1))
    repo_url = cast(str, job.get("repo_url", ""))

    if repo_url.startswith("local://"):
        repo_path = repo_url.removeprefix("local://")
        languages = await fetcher.detect_languages(repo_path)
        files = await fetcher.get_source_files(repo_path)
        loc = await fetcher.count_loc(repo_path)
        logger.info("local_repo_scan", path=repo_path, files=len(files))
    else:
        repo_path = await fetcher.clone(
            clone_url=repo_url,
            branch=cast(str, job["branch"]),
            depth=clone_depth,
            github_token=token,
        )
        languages = await fetcher.detect_languages(repo_path)
        files = await fetcher.get_source_files(repo_path)
        loc = await fetcher.count_loc(repo_path)

    language_lines: dict[str, int] = {}
    for f in files:
        lang = f.get("language", "unknown") or "unknown"
        language_lines[lang] = language_lines.get(lang, 0) + (
            f.get("lines_count", 0) or 0
        )
    total_lang_lines = sum(language_lines.values()) or 1
    language_breakdown = sorted(
        [
            {"name": lang, "percentage": round(count / total_lang_lines * 100, 1)}
            for lang, count in language_lines.items()
        ],
        key=lambda x: -x["percentage"],
    )

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
        # `languages_detected` and `language_breakdown` are columns on the job
        # row that nothing had ever written to. The breakdown was computed right
        # above, to a tenth of a percent, and then thrown away: it only lived in
        # this stage's return value and reached the reports table at finalize,
        # hours later for a slow repository. Writing it here means a reader
        # watching a running job sees the real language mix from 15% instead of
        # a placeholder. The reconstruction path in the report repository reads
        # these same columns, and was therefore always returning empty lists.
        languages_detected=languages,
        language_breakdown=language_breakdown,
    )

    result = {
        "repo_path": repo_path,
        "languages": languages,
        "language_breakdown": language_breakdown,
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


async def handle_stage_churn(
    cmd: ProcessStageCommand, uow: UnitOfWork, repo_path: str, depth: int
) -> list[dict[str, object]]:
    job = await uow.jobs.get_by_id(cmd.job_id)
    if not job:
        raise NotFoundError(f"Job {cmd.job_id} not found")

    from app.workers.churn.analyser import ChurnAnalyser, finding_from_churn

    analyser = ChurnAnalyser(repo_path, depth=depth)
    churn_results = await analyser.analyse()

    if churn_results:
        findings = [
            finding_from_churn(
                c,
                job_id=cmd.job_id,
                repo_id=job["repo_id"],
                workspace_id=job["workspace_id"],
            )
            for c in churn_results
        ]
        finding_entities = [
            Finding(
                job_id=cmd.job_id,
                repo_id=cast(UUID, f["repo_id"]),
                workspace_id=cast(UUID, f["workspace_id"]),
                rule_id=f["rule_id"],
                category=Category(f["category"]),
                severity=Severity(f["severity"]),
                title=f["title"],
                description=f["description"],
                recommendation=f["recommendation"],
                file_path=f["file_path"],
                score_impact=cast(float, f["score_impact"]),
                rpm_impact=cast(int, f.get("rpm_impact", 0)),
                metadata={
                    "change_count": c.change_count,
                    "unique_authors": c.unique_authors,
                },
            )
            for c, f in zip(churn_results, findings, strict=False)
        ]

        saved = await uow.findings.save_many(finding_entities)
        logger.info("churn_findings_saved", count=saved, job_id=str(cmd.job_id))

    await uow.jobs.update_status(
        cmd.job_id,
        JobStatus.CHURN,
        progress_pct=18,
        progress_message=f"Churn analysis: {len(churn_results)} hotspot files",
    )

    return [r.to_dict() for r in churn_results]


async def _push_progress(
    job_id: UUID,
    status: str,
    pct: int,
    message: str,
    engine_statuses: EngineStateMap | None = None,
) -> None:
    from sqlalchemy import update

    from app.infrastructure.db.models.analysis_job import AnalysisJobModel
    from app.infrastructure.db.session import async_session_factory

    async with async_session_factory() as session:
        values: dict[str, object] = {
            "status": status,
            "progress_pct": pct,
            "progress_message": message,
        }
        if engine_statuses is not None:
            values["engine_statuses"] = engine_statuses
        stmt = (
            update(AnalysisJobModel)
            .where(AnalysisJobModel.id == job_id)
            .values(**values)
        )
        await session.execute(stmt)
        await session.commit()


async def _push_engine_statuses(job_id: UUID, engine_statuses: EngineStateMap) -> None:
    """Persist engine status transitions on their own.

    `_push_progress` rewrites status/progress_pct/progress_message too, and
    those do not change when an engine finishes. Writing the whole row for every
    transition risks clobbering a concurrent stage write, so engine transitions
    get a narrow update of just the JSON column.
    """
    from sqlalchemy import update

    from app.infrastructure.db.models.analysis_job import AnalysisJobModel
    from app.infrastructure.db.session import async_session_factory

    async with async_session_factory() as session:
        stmt = (
            update(AnalysisJobModel)
            .where(AnalysisJobModel.id == job_id)
            .values(engine_statuses=engine_statuses)
        )
        await session.execute(stmt)
        await session.commit()


def _coerce_engine_statuses(statuses: object) -> EngineStateMap:
    """Normalise any engine-status shape into the wire shape.

    The pipeline builds this shape. The scorer's `display_statuses` is a plain
    string map, and rows written before per-engine timings existed hold strings
    too, so upgrade rather than writing a second shape into the same column.
    """
    if not isinstance(statuses, dict):
        return {}
    coerced: EngineStateMap = {}
    for engine_id, value in statuses.items():
        if isinstance(value, dict):
            coerced[str(engine_id)] = {
                "status": str(value.get("status", EngineStatus.PENDING)),
                "started_at": value.get("started_at"),
                "ended_at": value.get("ended_at"),
                "error": str(value.get("error", "")),
            }
        else:
            coerced[str(engine_id)] = {
                "status": str(value),
                "started_at": None,
                "ended_at": None,
                "error": "",
            }
    return coerced


async def handle_stage_parse(
    cmd: ProcessStageCommand,
    parser: ChainedParser,
    uow: UnitOfWork,
    producer: EventProducer,
    repo_path: str,
    files: list[dict[str, object]],
    languages: list[str],
    frameworks: list[str],
) -> tuple[list[dict[str, object]], list[ParsedFile]]:
    parsed: list[ParsedFile] = []
    errors = 0
    total = len(files)
    # Written every 10 points of progress rather than every tick, so a long
    # repository does not turn each 5-file batch into an UPDATE. Ten writes over
    # the stage is also more often than the frontend's 2s poll can notice.
    last_checkpoint = -1
    for i, f in enumerate(files):
        try:
            pf = await parser.parse(cast(str, f["path"]), cast(str, f["content"]))
            parsed.append(pf)
        except Exception:
            errors += 1
            logger.warning("parse_failed", path=f["path"], job_id=str(cmd.job_id))

        if (i + 1) % 5 == 0 or i == total - 1:
            pct = 25 + int(35 * (i + 1) / total)
            checkpoint = pct // 10
            if checkpoint != last_checkpoint:
                last_checkpoint = checkpoint
                await handle_save_analysis_metadata(
                    job_id=cmd.job_id,
                    parsed=parsed,
                    languages=languages,
                    frameworks=frameworks,
                    uow=uow,
                )
                # Committed here on purpose: the frontend polls this job through
                # its own session, so holding the totals until parse finished
                # would defeat the point of writing them early. Nothing else is
                # pending on this transaction at this point in the stage.
                await uow.commit()
            await _push_progress(
                cmd.job_id,
                JobStatus.PARSING,
                pct,
                f"Parsing files... ({i + 1}/{total})",
            )

    if last_checkpoint < 0:
        # No loop iteration ever reached a checkpoint: either the repository has
        # no source files, or there were fewer than the tick interval. A job must
        # end up with a metadata row either way, recording zeros rather than
        # nothing, or the metadata endpoint has no answer to give for this run.
        await handle_save_analysis_metadata(
            job_id=cmd.job_id,
            parsed=parsed,
            languages=languages,
            frameworks=frameworks,
            uow=uow,
        )
        await uow.commit()

    if errors:
        logger.warning(
            "parse_errors", count=errors, total=len(files), job_id=str(cmd.job_id)
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
        (
            f"Parsed {len(parsed)} files ({errors} errors)"
            if errors
            else f"Parsed {len(parsed)} files"
        ),
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
                rule_violations = await rule.analyze(pf.path, pf.content, ast_data)
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
            breaks_at_users=(
                perf_metrics.breaks_at_concurrent_users if perf_metrics else None
            ),
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
    language_breakdown: list[dict],
    total_files: int,
    total_lines: int,
    duration_seconds: int,
    engine_statuses: EngineStateMap | None = None,
) -> Report:
    get_settings()

    report = Report(
        job_id=cmd.job_id,
        repo_id=cast(UUID, job["repo_id"]),
        workspace_id=cast(UUID, job["workspace_id"]),
        branch=cast(str, job["branch"]),
        languages_detected=languages,
        language_breakdown=language_breakdown,
        total_files_analyzed=total_files,
        total_lines_of_code=total_lines,
        scores=score,
        findings=findings,
        duration_seconds=duration_seconds,
    )

    report_json = json.dumps(report.to_dict(), indent=2, default=str).encode("utf-8")

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
        # The pipeline's engine map, not score.engine_statuses.
        #
        # `score.engine_statuses` is the *scorer's* display view, built from
        # CATEGORY_ORDER -- the five scoring categories (performance, security,
        # reliability, maintainability, devops). Writing it over the pipeline's
        # map silently deleted dead_code, error_detection and simulation, so a
        # fully completed job reported 5 of its 8 engines and the other three
        # vanished rather than showing as completed. A scoring view is not a
        # record of which engines ran.
        engine_statuses=(
            _coerce_engine_statuses(engine_statuses)
            if engine_statuses is not None
            else _coerce_engine_statuses(score.engine_statuses)
        ),
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
        # Written at clone too, so a completed job's row carries the same values
        # whether or not that earlier write landed. This is the authoritative
        # point: whatever clone detected, finalize is what the report was built
        # from.
        languages_detected=languages,
        language_breakdown=language_breakdown,
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
    engine_statuses: EngineStateMap | None = None,
) -> None:
    # Reduced once, here, at the single point every failure path passes through.
    # Both the row and the event get the same string, so the page and any
    # notification built from it cannot disagree about what went wrong -- and a
    # fourth caller cannot forget, which is the failure mode that left the engine
    # column's guard one line short of this one.
    described = describe_failure(stage, error_message)

    try:
        job = await uow.jobs.get_by_id(job_id)
    except Exception:
        job = None

    if job:
        # Without engine_statuses the failed engines were lost: the pipeline had
        # already set them to "failed" in memory, but nothing carried that map
        # through to the row, so every engine still read "running" or "pending"
        # on a job that had already halted.
        #
        # progress_pct is deliberately omitted: the bar should stay where the
        # run actually got to, not snap back to 0. It used to reset to 0 here,
        # so a job that failed at 90% rendered as "0% - failed" and looked like
        # it had never done any work. The failure message names the stage.
        #
        # completed_at is written here because the run did end, and that column
        # means when the run ended. Only finalize wrote it before, so every failed
        # job was a terminal state with no terminal instant -- which left the
        # frontend unable to say how long a failed run had been going and unable
        # to distinguish "failed just now" from "failed three weeks ago" without
        # measuring against the current time.
        await uow.jobs.update_status(
            job_id,
            JobStatus.FAILED,
            progress_message=f"Failed at stage: {stage}",
            error_message=described,
            completed_at=datetime.now(UTC).replace(tzinfo=None),
            engine_statuses=_coerce_engine_statuses(engine_statuses),
        )

    # The event goes to subscribers, which render it into notifications. It gets
    # the described form for the same reason the column does: a notification is
    # shown to people who did not run the pipeline, and the traceback is both
    # unreadable at that size and a disclosure of server paths.
    try:
        await asyncio.wait_for(
            producer.publish(
                AnalysisFailed(
                    job_id=job_id,
                    repo_id=cast(UUID, job["repo_id"]) if job else UUID(int=0),
                    error_message=described,
                    stage=stage,
                )
            ),
            timeout=5,
        )
    except Exception:
        logger.warning("analysis_failed_publish_failed", job_id=str(job_id))

    # The raw exception stays here. This is the one line that gets the traceback,
    # and it is the reason the column and the event above can safely do without.
    logger.error(
        "analysis_failed", job_id=str(job_id), stage=stage, error=error_message
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
        logger.info("dead_code_saved", count=len(entries), job_id=str(cmd.job_id))

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
        logger.info("errors_saved", count=len(entries), job_id=str(cmd.job_id))

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
            "reliability_findings_saved", count=len(entries), job_id=str(cmd.job_id)
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
            "maintainability_findings_saved", count=len(entries), job_id=str(cmd.job_id)
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
        logger.info("devops_findings_saved", count=len(entries), job_id=str(cmd.job_id))

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
                "perf_metrics_saved", count=len(entries), job_id=str(cmd.job_id)
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
                "simulation_complete", job_id=str(cmd.job_id), statuses=statuses
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
        logger.warning("guide_gen_failed", job_id=str(cmd.job_id), error=str(exc))
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
        # `None`, not `""`: there was nothing to summarise, which is a different
        # statement from "the summary failed", and this dict is the return value
        # the pipeline puts in the shared run state.
        return {"findings": [], "ai_executive_summary": None}

    client = AiEnrichmentClient()
    outcome = await client.enrich_findings(
        findings=cast(list[dict[str, object]], finding_dicts),
        overall_score=score.overall if score else None,
        tier=str(score.tier) if score and score.tier else None,
        languages=languages,
        frameworks=frameworks,
    )

    if outcome.result is None:
        # A transport failure, not a generation failure, and now distinguishable
        # from one. The reason is persisted rather than logged and dropped: the
        # findings themselves were already computed and are about to be saved, so
        # the one thing missing is the summary -- and the user will see a completed
        # run with an empty card unless something says why.
        reason = _readable_summary_error(outcome.error)
        logger.error(
            "ai_enrichment_unavailable",
            job_id=str(job_id),
            reason=reason.get("code") if reason else "not_reported",
            message="AI service did not return an enrichment",
        )

        guide = await uow.enterprise_guides.get_by_job(job_id)
        if guide is not None:
            guide["ai_summary_error"] = reason
            await uow.enterprise_guides.save(guide)

        await uow.jobs.update_status(
            job_id,
            JobStatus.AI_ENRICH,
            progress_pct=98,
            progress_message="AI enrichment skipped (service unavailable)",
        )
        return None

    result = outcome.result

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

    # `ai_executive_summary` is `str | None` on the wire now, and this line was
    # `str(result.get("ai_executive_summary", ""))` -- which turned the AI
    # service's `None` back into `""`. The type change upstream is worth nothing
    # if this coerces it away, and it did: a failed summary and a summary nobody
    # asked for both became an empty string, and the `if` below treated them
    # identically.
    raw_summary = result.get("ai_executive_summary")
    ai_executive_summary = raw_summary if isinstance(raw_summary, str) else None

    # The AI service sends this only when the summary failed, and builds it from
    # named fields on `ClassifiedError` -- so what arrives has already been
    # reduced to code / message / suggested_action / retry_after. Re-validated
    # here rather than trusted: this is a network boundary between two services
    # that deploy independently, and the consequence of a widened envelope would
    # be a leaked provider error body landing in a column the guide endpoint
    # serves to browsers.
    summary_error = _readable_summary_error(result.get("ai_summary_error"))

    guide = await uow.enterprise_guides.get_by_job(job_id)
    if guide is None:
        # Unchanged behaviour, but no longer conditional on having a summary: a
        # failed summary is worth logging just as a saved one is, and the old
        # `if ai_executive_summary` nesting meant a failure logged a different
        # message than a success logged nothing about.
        logger.warning(
            "ai_enrichment_guide_not_found",
            job_id=str(job_id),
            message="Enterprise guide not found — cannot save AI summary",
        )
    elif ai_executive_summary:
        guide["ai_executive_summary"] = ai_executive_summary
        # A successful summary clears any error left by an earlier attempt. Without
        # this, a re-enrich that succeeds leaves the previous failure in place and
        # the UI shows both a summary and the reason it could not be written.
        guide["ai_summary_error"] = None
        await uow.enterprise_guides.save(guide)
        logger.info(
            "ai_enrichment_summary_saved",
            job_id=str(job_id),
            summary_length=len(ai_executive_summary),
        )
    else:
        guide["ai_summary_error"] = summary_error
        await uow.enterprise_guides.save(guide)
        logger.warning(
            "ai_enrichment_summary_failed",
            job_id=str(job_id),
            # The code, not the provider's words: the log is where technical detail
            # belongs, but the envelope is what crossed the boundary.
            reason=summary_error.get("code") if summary_error else "not_reported",
            # Distinguishes "the AI service said nothing" from "it said the summary
            # was empty", which were the same event before and are not now.
            reported=summary_error is not None,
            message="No AI executive summary — see ai_summary_error",
        )

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
        has_summary=bool(ai_executive_summary),
    )
    return result


async def handle_re_generate_guide(
    cmd: ProcessStageCommand, uow: UnitOfWork
) -> dict[str, object] | None:
    job_id = cmd.job_id
    job = await uow.jobs.get_by_id(job_id)
    if not job:
        raise NotFoundError(f"Job {job_id} not found")

    try:
        from types import SimpleNamespace

        # Load main Finding entities (duck-types as RuleViolation for the generator)
        findings, _ = await uow.findings.get_by_job(
            job_id, include_dismissed=True, limit=9999
        )

        # Load auxiliary finding tables as dicts, wrap for getattr compatibility
        def _to_objs(items: list[dict[str, object]]) -> list[object]:
            return [SimpleNamespace(**d) for d in items]

        dead_code = _to_objs(await uow.dead_code.get_by_job(job_id))
        errors = _to_objs(await uow.error_findings.get_by_job(job_id))
        reliability = _to_objs(await uow.reliability_findings.get_by_job(job_id))
        devops = _to_objs(await uow.devops_findings.get_by_job(job_id))
        maintainability = _to_objs(
            await uow.maintainability_findings.get_by_job(job_id)
        )

        # Reconstruct PerformanceMetrics from DB endpoint metrics
        from app.workers.perf.rpm_calculator import EndpointMetric, PerformanceMetrics

        perf_metrics: PerformanceMetrics | None = None
        pm_raw = await uow.performance_metrics.get_by_job(job_id)
        if pm_raw:
            endpoints: list[EndpointMetric] = []
            for m in pm_raw:
                endpoints.append(
                    EndpointMetric(
                        endpoint=m.get("endpoint", ""),
                        method=m.get("http_method", "GET"),
                        estimated_rpm=m.get("estimated_rpm", 0),
                        p50_latency_ms=m.get("p50_latency_ms", 0),
                        p95_latency_ms=m.get("p95_latency_ms", 0),
                        p99_latency_ms=m.get("p99_latency_ms", 0),
                        max_concurrent_users=m.get("max_concurrent_users", 0),
                        bottlenecks=(
                            [m["bottleneck_type"]] if m.get("bottleneck_type") else []
                        ),
                    )
                )
            perf_metrics = PerformanceMetrics(endpoints=endpoints)
            perf_metrics.overall_rpm = min(
                em.estimated_rpm for em in perf_metrics.endpoints
            )
            perf_metrics.breaks_at_concurrent_users = min(
                em.max_concurrent_users for em in perf_metrics.endpoints
            )
            all_bottlenecks: list[str] = []
            for em in perf_metrics.endpoints:
                all_bottlenecks.extend(em.bottlenecks)
            perf_metrics.bottlenecks = list(set(all_bottlenecks))
            perf_metrics.overall_confidence = min(
                em.confidence for em in perf_metrics.endpoints
            )

        # Load simulation results (dicts → SimulationResult objects)
        from app.workers.perf.load_sim import SimulationResult

        sim_raw = await uow.simulation_results.get_by_job(job_id)
        simulation: list[SimulationResult] = []
        for s in sim_raw or []:
            simulation.append(
                SimulationResult(
                    concurrent_users=s.get("concurrent_users", 0),
                    status=s.get("status", "unknown"),
                    overall_rpm=s.get("overall_rpm", 0),
                    error_rate_pct=s.get("error_rate_pct", 0.0),
                    bottlenecks=s.get("bottlenecks", []),
                    endpoints_analysis=s.get("endpoints_analysis", []),
                )
            )

        # Reconstruct Score from job record
        score = (
            Score(
                overall=job.get("overall_score"),
                performance=job.get("performance_score"),
                security=job.get("security_score"),
                reliability=job.get("reliability_score"),
                maintainability=job.get("maintainability_score"),
                devops=job.get("devops_score"),
                blocked_by=job.get("blocked_by") or [],
                engine_statuses=job.get("engine_statuses") or {},
            )
            if job.get("overall_score") is not None
            else Score(overall=0)
        )

        # Run generator — Finding duck-types as RuleViolation,
        # SimpleNamespace objects work with getattr() in _group_findings_by_severity,
        # and _flat() now handles Finding + dict/SimpleNamespace
        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(
            findings=findings,
            scores=score,
            perf_metrics=perf_metrics,
            simulation=simulation,
            dead_code=dead_code,
            errors=errors,
            reliability=reliability,
            devops=devops,
            maintainability=maintainability,
        )

        guide_dict = guide.to_dict()
        guide_dict["job_id"] = job_id
        guide_dict["repo_id"] = job["repo_id"]
        guide_dict["workspace_id"] = job["workspace_id"]

        # Preserve existing guide ID so merge() doesn't create a duplicate row
        existing = await uow.enterprise_guides.get_by_job(job_id)
        if existing and existing.get("id"):
            guide_dict["id"] = existing["id"]
            guide_dict.update(_carried_across_regeneration(existing))

        await uow.enterprise_guides.save(guide_dict)
        logger.info("enterprise_guide_regenerated", job_id=str(job_id))
        return guide_dict
    except Exception as exc:
        logger.warning("guide_regenerate_failed", job_id=str(job_id), error=str(exc))
        return None


async def handle_re_enrich(
    cmd: ProcessStageCommand, uow: UnitOfWork
) -> dict[str, object] | None:
    job_id = cmd.job_id
    job = await uow.jobs.get_by_id(job_id)
    if not job:
        raise NotFoundError(f"Job {job_id} not found")

    # Regenerate structured guide fields from existing analysis data first
    await handle_re_generate_guide(cmd, uow)

    findings, _ = await uow.findings.get_by_job(
        job_id, include_dismissed=True, limit=9999
    )

    score = (
        Score(
            overall=job.get("overall_score"),
            performance=job.get("performance_score"),
            security=job.get("security_score"),
            reliability=job.get("reliability_score"),
            maintainability=job.get("maintainability_score"),
            devops=job.get("devops_score"),
            blocked_by=job.get("blocked_by") or [],
            engine_statuses=job.get("engine_statuses") or {},
        )
        if job.get("overall_score") is not None
        else None
    )

    metadata = await uow.analysis_metadata.get_by_job(job_id)
    languages = list(metadata.languages) if metadata else None
    frameworks = list(metadata.frameworks) if metadata else None

    return await handle_stage_ai_enrich(
        cmd, uow, findings, score=score, languages=languages, frameworks=frameworks
    )


async def get_job_status(
    query: GetJobStatusQuery, uow: UnitOfWork
) -> dict[str, object] | None:
    return await uow.jobs.get_by_id(query.job_id)


async def list_findings(
    query: ListFindingsQuery, uow: UnitOfWork
) -> tuple[list[Finding], int]:
    return await uow.findings.get_by_job(
        query.job_id,
        category=query.category,
        severity=query.severity,
        include_dismissed=query.include_dismissed,
        limit=query.limit,
        offset=query.offset,
    )


async def dismiss_findings(command: DismissFindingsCommand, uow: UnitOfWork) -> int:
    return await uow.findings.dismiss_many(command.finding_ids)


async def get_findings_summary(
    query: GetFindingsSummaryQuery, uow: UnitOfWork
) -> dict[str, object]:
    by_severity = await uow.findings.count_by_severity(query.job_id)
    by_category = await uow.findings.count_by_category(query.job_id)
    return {"by_severity": by_severity, "by_category": by_category}


async def get_report(query: GetReportQuery, uow: UnitOfWork) -> Report | None:
    if query.report_id:
        return await uow.reports.get_by_job(query.report_id)
    if query.job_id:
        return await uow.reports.get_by_job(query.job_id)
    return None


async def list_jobs(query: ListJobsQuery, uow: UnitOfWork) -> dict[str, object]:
    if query.repo_id:
        jobs, total = await uow.jobs.list_by_repo(
            query.repo_id, limit=query.limit, offset=query.offset
        )
        return {"jobs": jobs, "total": total}
    if query.workspace_id:
        jobs, total = await uow.jobs.list_by_workspace(
            query.workspace_id, limit=query.limit, offset=query.offset
        )
        return {"jobs": jobs, "total": total}
    return {"jobs": [], "total": 0}


async def handle_delete_job(
    cmd: DeleteJobCommand, uow: UnitOfWork, storage: AbstractStorage | None = None
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


async def get_job_statistics(
    query: GetJobStatisticsQuery, uow: UnitOfWork
) -> dict[str, object]:
    from app.infrastructure.db.repositories.dead_code import DeadCodeRepository
    from app.infrastructure.db.repositories.enterprise_guide import (
        EnterpriseGuideRepository,
    )
    from app.infrastructure.db.repositories.error_finding import ErrorFindingRepository
    from app.infrastructure.db.repositories.finding import FindingRepository
    from app.infrastructure.db.repositories.performance_metric import (
        PerformanceMetricRepository,
    )
    from app.infrastructure.db.repositories.simulation_result import (
        SimulationResultRepository,
    )
    from app.infrastructure.db.session import async_session_factory

    async def _with_session(
        repo_cls: type[object], method: str, *args: object
    ) -> object:
        async with async_session_factory() as s:
            return await getattr(repo_cls(s), method)(*args)

    severity_counts, dc, err, perf, sim, guide_exists, cat_counts = (
        await asyncio.gather(
            _with_session(FindingRepository, "count_by_severity", query.job_id),
            _with_session(DeadCodeRepository, "count_by_job", query.job_id),
            _with_session(ErrorFindingRepository, "count_by_job", query.job_id),
            _with_session(PerformanceMetricRepository, "count_by_job", query.job_id),
            _with_session(SimulationResultRepository, "count_by_job", query.job_id),
            _with_session(EnterpriseGuideRepository, "exists_by_job", query.job_id),
            _with_session(FindingRepository, "count_by_category", query.job_id),
        )
    )

    findings_count = sum(severity_counts.values()) if severity_counts else 0

    return {
        "findings_count": findings_count,
        "dead_code_count": dc,
        "error_findings_count": err,
        "performance_metrics_count": perf,
        "simulation_results_count": sim,
        "enterprise_guide_exists": guide_exists,
        "counts_by_severity": severity_counts,
        "counts_by_category": cat_counts,
    }


async def get_dead_code(job_id: UUID, uow: UnitOfWork) -> list[dict[str, object]]:
    return await uow.dead_code.get_by_job(job_id)


async def get_error_findings(job_id: UUID, uow: UnitOfWork) -> list[dict[str, object]]:
    return await uow.error_findings.get_by_job(job_id)


async def get_performance_metrics(
    job_id: UUID, uow: UnitOfWork
) -> list[dict[str, object]]:
    return await uow.performance_metrics.get_by_job(job_id)


async def get_simulation_results(
    job_id: UUID, uow: UnitOfWork
) -> list[dict[str, object]]:
    return await uow.simulation_results.get_by_job(job_id)


async def get_enterprise_guide(
    job_id: UUID, uow: UnitOfWork
) -> dict[str, object] | None:
    return await uow.enterprise_guides.get_by_job(job_id)


def _count_code_entities(parsed: Sequence[ParsedFile]) -> tuple[int, int, int]:
    """Total (classes, functions, routes) across the files parsed so far.

    One counting path for both the running total written during parse and the
    final one, so the number a reader sees mid-run cannot drift from the number
    they see afterwards.
    """
    return (
        sum(len(p.classes) for p in parsed),
        sum(len(p.functions) for p in parsed),
        sum(len(p.routes) for p in parsed),
    )


async def handle_save_analysis_metadata(
    job_id: UUID,
    parsed: Sequence[ParsedFile],
    languages: list[str],
    frameworks: list[str],
    uow: UnitOfWork,
) -> None:
    """Persist the code-entity totals for a job, overwriting any earlier total.

    Called repeatedly while parse is still running, so that a reader polling a
    job in progress sees real counts from about 25% rather than skeletons until
    the whole repository has been parsed.
    """
    class_count, function_count, endpoint_count = _count_code_entities(parsed)

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
        files=len(parsed),
    )


async def get_analysis_metadata(
    job_id: UUID, uow: UnitOfWork
) -> AnalysisMetadata | None:
    return await uow.analysis_metadata.get_by_job(job_id)
