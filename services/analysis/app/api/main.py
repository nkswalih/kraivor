import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.middleware.error_handler import (
    generic_exception_handler,
    not_found_handler,
)
from app.api.middleware.logging import RequestLoggingMiddleware
from app.api.middleware.request_id import RequestIDMiddleware
from app.api.routers import (
    dead_code_router,
    devops_findings_router,
    enterprise_guide_router,
    error_findings_router,
    files_router,
    findings_router,
    health_router,
    jobs_router,
    maintainability_findings_router,
    performance_metrics_router,
    reliability_findings_router,
    reports_router,
    score_history_router,
    simulation_results_router,
)
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"


class StripTrailingSlashMiddleware:
    """Strip trailing slashes from request paths to prevent 307 redirects."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["path"] != "/"
            and scope["path"].endswith("/")
        ):
            scope["path"] = scope["path"].rstrip("/")
        await self.app(scope, receive, send)


async def run_migrations() -> None:
    proc = await asyncio.create_subprocess_exec(
        "alembic",
        "-c",
        str(MIGRATIONS_DIR / "alembic.ini"),
        "upgrade",
        "head",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error(
            "migration_failed",
            returncode=proc.returncode,
            stderr=stderr.decode(errors="replace"),
            stdout=stdout.decode(errors="replace"),
        )
        raise RuntimeError(
            f"Alembic migration failed: {stderr.decode(errors='replace')}"
        )
    logger.info("migrations_applied")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    get_settings()
    logger.info("starting", service="analysis-service", version="0.1.0")
    await run_migrations()
    yield
    logger.info("shutting_down", service="analysis-service")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Analysis Service",
        description="Production readiness analysis for source code repositories",
        version="0.1.0",
        lifespan=lifespan,
        redirect_slashes=False,
    )

    app.add_middleware(StripTrailingSlashMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(files_router)
    app.include_router(findings_router)
    app.include_router(reports_router)
    app.include_router(dead_code_router)
    app.include_router(devops_findings_router)
    app.include_router(error_findings_router)
    app.include_router(reliability_findings_router)
    app.include_router(maintainability_findings_router)
    app.include_router(performance_metrics_router)
    app.include_router(score_history_router)
    app.include_router(simulation_results_router)
    app.include_router(enterprise_guide_router)

    app.add_exception_handler(NotFoundError, not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)

    return app
