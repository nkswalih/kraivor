from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.maintainability import (
    MaintainabilityFindingListResponse,
    MaintainabilityMetricsResponse,
    MaintainabilityFindingResponse,
)
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/maintainability-findings", tags=["maintainability-findings"])


@router.get("", response_model=MaintainabilityFindingListResponse)
async def list_maintainability_findings(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> MaintainabilityFindingListResponse:
    findings = await uow.maintainability_findings.get_by_job(job_id)
    return MaintainabilityFindingListResponse(
        findings=[MaintainabilityFindingResponse(**f) for f in findings],
        total=len(findings),
    )


@router.get("/metrics", response_model=MaintainabilityMetricsResponse)
async def get_maintainability_metrics(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> MaintainabilityMetricsResponse:
    metrics = await uow.maintainability_findings.get_metrics_by_job(job_id)
    if metrics is None:
        return MaintainabilityMetricsResponse()
    return MaintainabilityMetricsResponse(
        maintainability_index=metrics.get("maintainability_index", 100.0),
        technical_debt_hours=metrics.get("technical_debt_hours", 0.0),
        complexity_score=metrics.get("complexity_score", 100.0),
        total_findings=metrics.get("total_findings", 0),
    )
