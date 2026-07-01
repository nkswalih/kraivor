from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.devops import DevOpsFindingListResponse, DevOpsFindingResponse
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/devops-findings", tags=["devops-findings"])


@router.get("", response_model=DevOpsFindingListResponse)
async def list_devops_findings(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> DevOpsFindingListResponse:
    findings = await uow.devops_findings.get_by_job(job_id)
    return DevOpsFindingListResponse(
        findings=[DevOpsFindingResponse(**f)  for f in findings],  # type: ignore[arg-type]
        total=len(findings),
    )
