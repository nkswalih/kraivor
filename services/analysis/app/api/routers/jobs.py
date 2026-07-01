import asyncio
from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.services import get_storage, get_uow
from app.api.schemas.jobs import (
    JobListResponse,
    JobStatusResponse,
    StartAnalysisRequest,
)
from app.application.analysis.commands import DeleteJobCommand, StartAnalysisCommand
from app.application.analysis.handler import (
    get_job_status,
    handle_analysis_failure,
    handle_delete_job,
    handle_start_analysis,
    list_jobs,
)
from app.application.analysis.queries import GetJobStatusQuery, ListJobsQuery
from app.application.tasks.pipeline import run_full_analysis
from app.core.constants import TriggerType
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.domain.contracts.storage import AbstractStorage
from app.infrastructure.db.unit_of_work import UnitOfWork
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

    background_task = asyncio.create_task(_run_analysis_safe({
        "job_id": str(job_id),
        "repo_id": str(body.repo_id),
        "workspace_id": str(body.workspace_id),
        "triggered_by": user.sub,
        "trigger_type": TriggerType.API,
        "repo_url": body.repo_url,
        "branch": body.branch,
        "deep_scan": body.deep_scan,
        "depth": body.depth,
    }))
    _background_tasks.add(background_task)
    background_task.add_done_callback(lambda t: _background_tasks.discard(t))

    job = await uow.jobs.get_by_id(job_id)
    return _job_to_response(job)  # type: ignore[arg-type]


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
    workspace_id: UUID | None = Query(None, description="Filter by workspace. Defaults to user's first workspace."),
    uow: UnitOfWork = Depends(get_uow),
    user: JWTPayload = Depends(get_current_user),
) -> JobListResponse:
    query = ListJobsQuery(
        workspace_id=workspace_id or (UUID(user.workspace_ids[0]) if user.workspace_ids else None),
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
        engine_statuses=cast(dict[str, str], job.get("engine_statuses") or {}),
        error_message=cast(str | None, job.get("error_message")),
        created_at=cast(datetime, job["created_at"]),
        started_at=cast(datetime | None, job.get("started_at")),
        completed_at=cast(datetime | None, job.get("completed_at")),
    )
