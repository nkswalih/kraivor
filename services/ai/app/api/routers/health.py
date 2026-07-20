from fastapi import APIRouter

from app.api.dependencies.backpressure import get_backpressure_stats
from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@router.get("/health/ready", response_model=HealthResponse)
async def readiness():
    return HealthResponse()


@router.get("/health/load")
async def load_stats():
    return get_backpressure_stats()
