from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.findings import (
    FindingsListResponse,
    FindingsSummaryResponse,
    FindingResponse,
)
from app.application.analysis.handler import (
    get_findings_summary,
    list_findings,
)
from app.application.analysis.queries import (
    GetFindingsSummaryQuery,
    ListFindingsQuery,
)
from app.core.logging import get_logger
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])


@router.get("/", response_model=FindingsListResponse)
async def list_findings_endpoint(
    job_id: UUID = Query(..., description="Filter by job ID"),
    severity: str | None = Query(None, description="Filter by severity"),
    category: str | None = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    uow: UnitOfWork = Depends(get_uow),
) -> FindingsListResponse:
    query = ListFindingsQuery(
        job_id=job_id,
        severity=severity,
        category=category,
        page=page,
        page_size=page_size,
    )
    result = await list_findings(query, uow)
    return FindingsListResponse(
        findings=[FindingResponse(**f) for f in result["findings"]],
        total=result["total"],
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=FindingsSummaryResponse)
async def findings_summary(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
) -> FindingsSummaryResponse:
    query = GetFindingsSummaryQuery(job_id=job_id)
    result = await get_findings_summary(query, uow)
    return FindingsSummaryResponse(
        job_id=str(job_id),
        total=result["total"],
        by_severity=result["by_severity"],
        by_category=result["by_category"],
    )
