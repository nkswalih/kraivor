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
    _user: JWTPayload = Depends(get_current_user),
) -> JobStatusResponse:
    cmd = StartAnalysisCommand(
        repo_url=body.repo_url,
        branch=body.branch,
        depth=body.depth,
    )
    job_id = await handle_start_analysis(cmd, uow, producer)
    job = await uow.jobs.get_by_id(job_id)
    return JobStatusResponse(
        job_id=str(job_id),
        status=job["status"],
        repo_url=body.repo_url,
        branch=body.branch,
        created_at=job["created_at"],
        updated_at=job["updated_at"],
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
        job_id=str(job["job_id"]),
        status=job["status"],
        repo_url=job["repo_url"],
        branch=job["branch"],
        progress_pct=job["progress_pct"],
        progress_message=job["progress_message"],
        total_files=job.get("total_files"),
        total_lines=job.get("total_lines"),
        frameworks=job.get("frameworks", []),
        error_message=job.get("error_message"),
        created_at=job["created_at"],
        updated_at=job["updated_at"],
    )


@router.get("/", response_model=JobListResponse)
async def list_jobs_endpoint(
    page: int = 1,
    page_size: int = 20,
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> JobListResponse:
    query = ListJobsQuery(page=page, page_size=page_size)
    result = await list_jobs(query, uow)
    return JobListResponse(
        jobs=[JobStatusResponse(**j) for j in result["jobs"]],
        total=result["total"],
        page=page,
        page_size=page_size,
    )
