from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.reliability import (
    ReliabilityFindingListResponse,
    ReliabilityFindingResponse,
)
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/reliability-findings", tags=["reliability-findings"])


@router.get("", response_model=ReliabilityFindingListResponse)
async def list_reliability_findings(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> ReliabilityFindingListResponse:
    findings = await uow.reliability_findings.get_by_job(job_id)
    return ReliabilityFindingListResponse(
        findings=[ReliabilityFindingResponse(**f) for f in findings],
        total=len(findings),
    )
