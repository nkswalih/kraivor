from app.api.routers.dead_code import router as dead_code_router
from app.api.routers.devops import router as devops_findings_router
from app.api.routers.errors import router as error_findings_router
from app.api.routers.files import router as files_router
from app.api.routers.findings import router as findings_router
from app.api.routers.guide import router as enterprise_guide_router
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.maintainability import router as maintainability_findings_router
from app.api.routers.perf import router as performance_metrics_router
from app.api.routers.reliability import router as reliability_findings_router
from app.api.routers.reports import router as reports_router
from app.api.routers.score_history import router as score_history_router
from app.api.routers.simulation import router as simulation_results_router

__all__ = [
    "dead_code_router",
    "devops_findings_router",
    "enterprise_guide_router",
    "error_findings_router",
    "files_router",
    "findings_router",
    "health_router",
    "jobs_router",
    "maintainability_findings_router",
    "performance_metrics_router",
    "reliability_findings_router",
    "reports_router",
    "score_history_router",
    "simulation_results_router",
]
