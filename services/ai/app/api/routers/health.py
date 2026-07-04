from fastapi import APIRouter

from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@router.get("/health/ready", response_model=HealthResponse)
async def readiness():
    return HealthResponse()
