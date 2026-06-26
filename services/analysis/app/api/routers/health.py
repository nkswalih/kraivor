import time
from datetime import datetime

import httpx
import structlog
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.infrastructure.db.session import get_db_session

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"], prefix="/v1")


class DependencyHealth(BaseModel):
    status: str
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "analysis-service"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dependencies: dict[str, DependencyHealth] = {}


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    deps: dict[str, DependencyHealth] = {}

    start = time.monotonic()
    try:
        async for _ in get_db_session():
            pass
        deps["database"] = DependencyHealth(
            status="healthy",
            latency_ms=round((time.monotonic() - start) * 1000, 2),
        )
    except Exception as e:
        deps["database"] = DependencyHealth(
            status="unhealthy",
            error=str(e),
        )

    start = time.monotonic()
    try:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(str(settings.jwt.jwks_url))
            resp.raise_for_status()
        deps["identity"] = DependencyHealth(
            status="healthy",
            latency_ms=round((time.monotonic() - start) * 1000, 2),
        )
    except Exception as e:
        deps["identity"] = DependencyHealth(
            status="degraded",
            error=str(e),
        )

    overall = "ok"
    for _name, dep in deps.items():
        if dep.status == "unhealthy":
            overall = "degraded"

    return HealthResponse(
        status=overall,
        dependencies=deps,
    )


@router.get("/health/ready")
async def readiness_check() -> dict[str, object]:
    return {"status": "ready"}
