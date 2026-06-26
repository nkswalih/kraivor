from app.api.routers.dead_code import router as dead_code_router
from app.api.routers.errors import router as error_findings_router
from app.api.routers.findings import router as findings_router
from app.api.routers.guide import router as enterprise_guide_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.perf import router as performance_metrics_router
from app.api.routers.reports import router as reports_router
from app.api.routers.simulation import router as simulation_results_router

__all__ = [
    "dead_code_router",
    "enterprise_guide_router",
    "error_findings_router",
    "findings_router",
    "health_router",
    "jobs_router",
    "performance_metrics_router",
    "reports_router",
    "simulation_results_router",
]
