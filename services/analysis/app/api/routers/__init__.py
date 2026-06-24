from app.api.routers.findings import router as findings_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.reports import router as reports_router

__all__ = [
    "findings_router",
    "health_router",
    "jobs_router",
    "reports_router",
]
