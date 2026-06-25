from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.errors import ErrorFindingListResponse, ErrorFindingResponse
from app.application.analysis.handler import get_error_findings
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/error-findings", tags=["error-findings"])


@router.get("/", response_model=ErrorFindingListResponse)
async def list_error_findings(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> ErrorFindingListResponse:
    findings = await get_error_findings(job_id, uow)
    return ErrorFindingListResponse(
        findings=[ErrorFindingResponse(**f) for f in findings],
        total=len(findings),
    )
