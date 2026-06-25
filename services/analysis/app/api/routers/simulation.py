from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.simulation import (
    SimulationResultListResponse,
    SimulationResultResponse,
)
from app.application.analysis.handler import get_simulation_results
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/simulation-results", tags=["simulation-results"])


@router.get("/", response_model=SimulationResultListResponse)
async def list_simulation_results(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> SimulationResultListResponse:
    results = await get_simulation_results(job_id, uow)
    return SimulationResultListResponse(
        results=[SimulationResultResponse(**r) for r in results],
        total=len(results),
    )
