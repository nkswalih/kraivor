from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.error_handler import (
    generic_exception_handler,
    not_found_handler,
)
from app.api.middleware.logging import RequestLoggingMiddleware
from app.api.routers import (
    dead_code_router,
    enterprise_guide_router,
    error_findings_router,
    findings_router,
    health_router,
    jobs_router,
    performance_metrics_router,
    reports_router,
    simulation_results_router,
)
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    get_settings()
    logger.info("starting", service="analysis-service", version="0.1.0")
    yield
    logger.info("shutting_down", service="analysis-service")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Analysis Service",
        description="Production readiness analysis for source code repositories",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(findings_router)
    app.include_router(reports_router)
    app.include_router(dead_code_router)
    app.include_router(error_findings_router)
    app.include_router(performance_metrics_router)
    app.include_router(simulation_results_router)
    app.include_router(enterprise_guide_router)

    app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)

    return app
