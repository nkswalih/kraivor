from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.perf import (
    PerformanceMetricListResponse,
    PerformanceMetricResponse,
)
from app.application.analysis.handler import get_performance_metrics
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/performance-metrics", tags=["performance-metrics"])


@router.get("/", response_model=PerformanceMetricListResponse)
async def list_performance_metrics(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> PerformanceMetricListResponse:
    metrics = await get_performance_metrics(job_id, uow)
    return PerformanceMetricListResponse(
        metrics=[PerformanceMetricResponse(**m) for m in metrics],
        total=len(metrics),
    )
