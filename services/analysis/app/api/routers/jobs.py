from datetime import datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies.services import get_uow
from app.api.schemas.jobs import (
    JobListResponse,
    JobStatusResponse,
    StartAnalysisRequest,
)
from app.application.analysis.commands import StartAnalysisCommand
from app.application.analysis.handler import (
    get_job_status,
    handle_start_analysis,
    list_jobs,
)
from app.application.analysis.queries import GetJobStatusQuery, ListJobsQuery
from app.application.tasks.pipeline import run_full_analysis
from app.core.constants import TriggerType
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("/", response_model=JobStatusResponse, status_code=201)
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

    run_full_analysis.delay({
        "job_id": str(job_id),
        "repo_id": str(body.repo_id),
        "workspace_id": str(body.workspace_id),
        "triggered_by": user.sub,
        "trigger_type": TriggerType.API,
        "repo_url": body.repo_url,
        "branch": body.branch,
        "deep_scan": body.deep_scan,
        "depth": body.depth,
    })

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


@router.get("/", response_model=JobListResponse)
async def list_jobs_endpoint(
    page: int = 1,
    page_size: int = 20,
    uow: UnitOfWork = Depends(get_uow),
    user: JWTPayload = Depends(get_current_user),
) -> JobListResponse:
    query = ListJobsQuery(
        workspace_id=UUID(user.workspace_ids[0]) if user.workspace_ids else None,
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


def _job_to_response(job: dict[str, object]) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=str(job["id"]),
        repo_id=job["repo_id"],
        workspace_id=job["workspace_id"],
        status=cast(str, job["status"]),
        repo_url=cast(str, job["repo_url"]),
        branch=cast(str, job["branch"]),
        progress_pct=float(cast((str | int | float), job["progress_pct"])),
        progress_message=cast(str, job["progress_message"]) or "",
        total_findings=cast(int, job["total_findings"]),
        total_files=cast(int | None, job.get("total_files")),
        total_lines=cast(int | None, job.get("total_lines")),
        overall_score=cast(float | None, job.get("overall_score")),
        error_message=cast(str | None, job.get("error_message")),
        created_at=cast(datetime, job["created_at"]),
        started_at=cast(datetime | None, job.get("started_at")),
        completed_at=cast(datetime | None, job.get("completed_at")),
    )
