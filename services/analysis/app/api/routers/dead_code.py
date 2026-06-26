from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.dead_code import DeadCodeFindingResponse, DeadCodeListResponse
from app.application.analysis.handler import get_dead_code
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/dead-code", tags=["dead-code"])


@router.get("/", response_model=DeadCodeListResponse)
async def list_dead_code(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> DeadCodeListResponse:
    findings = await get_dead_code(job_id, uow)
    return DeadCodeListResponse(
        findings=[DeadCodeFindingResponse(**f) for f in findings],  # type: ignore[arg-type]
        total=len(findings),
    )
