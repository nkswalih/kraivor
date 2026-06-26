from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.guide import EnterpriseGuideResponse
from app.application.analysis.handler import get_enterprise_guide
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/enterprise-guide", tags=["enterprise-guide"])


@router.get("/", response_model=EnterpriseGuideResponse)
async def get_guide(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> EnterpriseGuideResponse:
    guide = await get_enterprise_guide(job_id, uow)
    if not guide:
        raise HTTPException(status_code=404, detail="Enterprise guide not found")
    return EnterpriseGuideResponse(**guide)  # type: ignore[arg-type]
