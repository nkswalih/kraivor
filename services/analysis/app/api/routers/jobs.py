import asyncio
from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.services import get_storage, get_uow
from app.api.schemas.jobs import (
    EngineInfo,
    EngineListResponse,
    EngineState,
    JobListResponse,
    JobStatisticsResponse,
    JobStatusResponse,
    LanguageShare,
    StartAnalysisRequest,
)
from app.application.analysis.commands import (
    DeleteJobCommand,
    ProcessStageCommand,
    StartAnalysisCommand,
)
from app.application.analysis.handler import (
    get_job_status,
    handle_analysis_failure,
    handle_delete_job,
    handle_re_enrich,
    handle_start_analysis,
    list_jobs,
)
from app.application.analysis.queries import (
    GetJobStatisticsQuery,
    GetJobStatusQuery,
    ListJobsQuery,
)
from app.application.tasks.pipeline import run_full_analysis
from app.core.constants import TriggerType
from app.core.engines import ENGINE_SPECS, EngineSpec
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.domain.contracts.storage import AbstractStorage
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.git.repository_fetcher import RepositoryFetcher
from app.infrastructure.messaging.producer import EventProducer

logger = get_logger(__name__)

_background_tasks: set[asyncio.Task[None]] = set()


async def _run_analysis_safe(cmd_dict: dict[str, object]) -> None:
    """Run the full analysis pipeline and catch any silent task exceptions.

    `asyncio.create_task` silently drops unhandled exceptions.
    This wrapper ensures any failure is logged and, as a last resort,
    marks the job as failed in the database so it doesn't stay stuck
    in 'queued' forever.
    """
    try:
        await run_full_analysis(cmd_dict)
    except Exception:
        logger.exception("analysis_task_crashed")
        job_id = cmd_dict.get("job_id")
        if job_id:
            try:
                async with UnitOfWork() as uow:
                    producer = EventProducer()
                    await handle_analysis_failure(
                        UUID(cast(str, job_id)),
                        "init",
                        "Background task crashed before pipeline started",
                        uow,
                        producer,
                    )
                    await uow.commit()
            except Exception:
                logger.exception("last_resort_failure_update_failed")


router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("", response_model=JobStatusResponse, status_code=201)
async def start_analysis(
    body: StartAnalysisRequest,
    uow: UnitOfWork = Depends(get_uow),
    user: JWTPayload = Depends(get_current_user),
) -> JobStatusResponse:
    cmd = StartAnalysisCommand(
        repo_id=body.repo_id,
        workspace_id=body.workspace_id,
        triggered_by=UUID(user.sub),
        trigger_type=TriggerType.API,
        repo_url=body.repo_url,
        branch=body.branch,
        deep_scan=body.deep_scan,
        depth=body.depth,
    )
    job_id = await handle_start_analysis(cmd, uow)
    await uow.commit()

    background_task = asyncio.create_task(
        _run_analysis_safe(
            {
                "job_id": str(job_id),
                "repo_id": str(body.repo_id),
                "workspace_id": str(body.workspace_id),
                "triggered_by": user.sub,
                "trigger_type": TriggerType.API,
                "repo_url": body.repo_url,
                "branch": body.branch,
                "deep_scan": body.deep_scan,
                "depth": body.depth,
            }
        )
    )
    _background_tasks.add(background_task)
    background_task.add_done_callback(lambda t: _background_tasks.discard(t))

    job = await uow.jobs.get_by_id(job_id)
    return _job_to_response(job)  # type: ignore[arg-type]


@router.get("/{job_id}/statistics", response_model=JobStatisticsResponse)
async def get_job_statistics(
    job_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> JobStatisticsResponse:
    from app.application.analysis.handler import get_job_statistics as _get_stats

    query = GetJobStatisticsQuery(job_id=job_id)
    stats = await _get_stats(query, uow)
    return JobStatisticsResponse(**stats)


@router.get("/branches")
async def list_branches(
    url: str = Query(..., description="Repository clone URL"),
    _user: JWTPayload = Depends(get_current_user),
) -> list[str]:
    fetcher = RepositoryFetcher()
    return await fetcher.list_branches(url)


@router.get("/engines", response_model=EngineListResponse)
async def list_engines(
    _user: JWTPayload = Depends(get_current_user),
) -> EngineListResponse:
    """The canonical engine catalogue.

    The UI used to hardcode its own engine keys, and the four copies of that
    list disagreed: the pipeline tracked 8 engines, the insights builder listed
    6, the job page listed 5, and `dead_code` and `error_detection` were in none
    of the frontend lists despite running on every analysis. Serving the
    catalogue means adding an engine cannot leave the UI behind.
    """
    return EngineListResponse(engines=[_engine_to_response(s) for s in ENGINE_SPECS])


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> JobStatusResponse:
    query = GetJobStatusQuery(job_id=job_id)
    job = await get_job_status(query, uow)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@router.get("", response_model=JobListResponse)
async def list_jobs_endpoint(
    page: int = 1,
    page_size: int = 20,
    workspace_id: UUID | None = Query(
        None, description="Filter by workspace. Defaults to user's first workspace."
    ),
    uow: UnitOfWork = Depends(get_uow),
    user: JWTPayload = Depends(get_current_user),
) -> JobListResponse:
    query = ListJobsQuery(
        workspace_id=workspace_id
        or (UUID(user.workspace_ids[0]) if user.workspace_ids else None),
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    result = await list_jobs(query, uow)
    jobs_list = cast(list[dict[str, object]], result["jobs"])
    return JobListResponse(
        jobs=[_job_to_response(j) for j in jobs_list],
        total=cast(int, result["total"]),
        page=page,
        page_size=page_size,
    )


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
    storage: AbstractStorage = Depends(get_storage),
    user: JWTPayload = Depends(get_current_user),
) -> None:
    cmd = DeleteJobCommand(
        job_id=job_id,
        workspace_id=UUID(user.workspace_ids[0]) if user.workspace_ids else UUID(int=0),
    )
    await handle_delete_job(cmd, uow, storage)
    await uow.commit()


@router.post("/{job_id}/re-enrich")
async def re_enrich_job(
    job_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
    user: JWTPayload = Depends(get_current_user),
) -> dict[str, object]:
    cmd = ProcessStageCommand(job_id=job_id, stage="ai_enrich")
    result = await handle_re_enrich(cmd, uow)
    await uow.commit()

    # `{"status": "ok"}` unconditionally, with `enriched` as the only signal, and
    # the client treating arrival as success. So a re-enrich that reached the AI
    # service and was refused, or timed out, or returned no summary, produced a
    # green "AI enrichment regenerated" toast on a run that had not been
    # enriched. `enriched` could not carry it either: it is `result is not None`,
    # and a failed summary is exactly the case where the stage still returns a
    # result -- the findings enrichment succeeded.
    #
    # The reason is read back off the guide rather than returned from the handler:
    # `handle_stage_ai_enrich` persists it, and re-reading is what makes this
    # agree with what a reload of the page will show.
    guide = await uow.enterprise_guides.get_by_job(job_id)
    summary_error = (guide or {}).get("ai_summary_error")
    has_summary = bool((guide or {}).get("ai_executive_summary"))

    return {
        # "degraded" rather than "ok" because the request did succeed -- findings
        # were re-enriched and the reason was recorded -- and calling it a failure
        # would tell the client to retry the whole thing when the retry would fail
        # the same way. `enriched` keeps its old meaning so nothing that reads it
        # changes behaviour.
        "status": "ok" if has_summary else "degraded",
        "enriched": result is not None,
        "has_summary": has_summary,
        "ai_summary_error": summary_error,
    }


def _engine_to_response(spec: EngineSpec) -> EngineInfo:
    return EngineInfo(
        key=spec.key,
        label=spec.label,
        description=spec.description,
        stage=spec.stage,
        score_category=spec.score_category,
    )


def _job_to_response(job: dict[str, object]) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=str(job["id"]),
        repo_id=cast(UUID, job["repo_id"]),
        workspace_id=cast(UUID, job["workspace_id"]),
        status=cast(str, job["status"]),
        repo_url=cast(str, job["repo_url"]),
        branch=cast(str, job["branch"]),
        progress_pct=float(cast((str | int | float), job["progress_pct"])),
        progress_message=cast(str, job["progress_message"]) or "",
        total_findings=cast(int, job["total_findings"]),
        total_files=cast(int | None, job.get("total_files")),
        total_lines=cast(int | None, job.get("total_lines")),
        overall_score=cast(int | None, job.get("overall_score")),
        blocked_by=cast(list[str], job.get("blocked_by") or []),
        # Not cast to dict[str, str]: the column holds the per-engine object
        # shape now, and EngineState upgrades any legacy string rows on read.
        engine_statuses=cast(dict[str, EngineState], job.get("engine_statuses") or {}),
        error_message=cast(str | None, job.get("error_message")),
        created_at=cast(datetime, job["created_at"]),
        started_at=cast(datetime | None, job.get("started_at")),
        completed_at=cast(datetime | None, job.get("completed_at")),
        # Left as None when the job has not reached clone yet, rather than
        # coerced to an empty list: the frontend needs the difference between
        # "no measurement yet" and "measured, and there were none".
        languages_detected=cast(list[str] | None, job.get("languages_detected")),
        language_breakdown=cast(
            list[LanguageShare] | None, job.get("language_breakdown")
        ),
    )
