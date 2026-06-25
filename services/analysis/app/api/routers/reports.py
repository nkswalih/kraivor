from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.reports import ReportResponse
from app.application.analysis.handler import get_report
from app.application.analysis.queries import GetReportQuery
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.domain.entities.report import Report
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/by-job/{job_id}", response_model=ReportResponse)
async def get_report_by_job(
    job_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> ReportResponse:
    query = GetReportQuery(job_id=job_id)
    report = await get_report(query, uow)
    if not report:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report not found")
    return _report_to_response(report)


def _report_to_response(report: Report) -> ReportResponse:
    scores = report.scores
    return ReportResponse(
        job_id=report.job_id,
        repo_id=report.repo_id,
        workspace_id=report.workspace_id,
        branch=report.branch,
        overall_score=scores.overall if scores else None,
        performance_score=scores.performance if scores else None,
        security_score=scores.security if scores else None,
        reliability_score=scores.reliability if scores else None,
        maintainability_score=scores.maintainability if scores else None,
        devops_score=scores.devops if scores else None,
        total_findings=scores.findings_count if scores else 0,
        total_files=report.total_files_analyzed,
        duration_seconds=report.duration_seconds,
        completed_at=report.completed_at,
    )
