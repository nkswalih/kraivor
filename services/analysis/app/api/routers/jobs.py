from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies.services import get_producer, get_uow
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
from app.infrastructure.messaging.producer import EventProducer

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post("/", response_model=JobStatusResponse, status_code=201)
async def start_analysis(
    body: StartAnalysisRequest,
    uow: UnitOfWork = Depends(get_uow),
    producer: EventProducer = Depends(get_producer),
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
    job_id = await handle_start_analysis(cmd, uow, producer)
    await uow.commit()

    run_full_analysis.delay({
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
    return JobStatusResponse(
        job_id=str(job["id"]),
        repo_id=job["repo_id"],
        workspace_id=job["workspace_id"],
        status=job["status"],
        repo_url=job["repo_url"],
        branch=job["branch"],
        progress_pct=float(job["progress_pct"]),
        progress_message=job["progress_message"] or "",
        total_findings=job["total_findings"],
        total_files=job.get("total_files"),
        total_lines=job.get("total_lines"),
        overall_score=job.get("overall_score"),
        error_message=job.get("error_message"),
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> JobStatusResponse:
    query = GetJobStatusQuery(job_id=job_id)
    job = await get_job_status(query, uow)
    return JobStatusResponse(
        job_id=str(job["id"]),
        repo_id=job["repo_id"],
        workspace_id=job["workspace_id"],
        status=job["status"],
        repo_url=job["repo_url"],
        branch=job["branch"],
        progress_pct=float(job["progress_pct"]),
        progress_message=job["progress_message"] or "",
        total_findings=job["total_findings"],
        total_files=job.get("total_files"),
        total_lines=job.get("total_lines"),
        overall_score=job.get("overall_score"),
        error_message=job.get("error_message"),
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
    )


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
    return JobListResponse(
        jobs=[JobStatusResponse(
            job_id=str(j["id"]),
            repo_id=j["repo_id"],
            workspace_id=j["workspace_id"],
            status=j["status"],
            repo_url=j["repo_url"],
            branch=j["branch"],
            progress_pct=float(j["progress_pct"]),
            progress_message=j["progress_message"] or "",
            total_findings=j["total_findings"],
            total_files=j.get("total_files"),
            total_lines=j.get("total_lines"),
            overall_score=j.get("overall_score"),
            error_message=j.get("error_message"),
            created_at=j["created_at"],
            started_at=j.get("started_at"),
            completed_at=j.get("completed_at"),
        ) for j in result["jobs"]],
        total=result["total"],
        page=page,
        page_size=page_size,
    )
