from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_uow
from app.api.schemas.reports import ReportResponse
from app.application.analysis.handler import get_report
from app.application.analysis.queries import GetReportQuery
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report_endpoint(
    report_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> ReportResponse:
    query = GetReportQuery(report_id=report_id)
    report = await get_report(query, uow)
    return ReportResponse(**report)


@router.get("/by-job/{job_id}", response_model=ReportResponse)
async def get_report_by_job(
    job_id: UUID,
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> ReportResponse:
    query = GetReportQuery(job_id=job_id)
    report = await get_report(query, uow)
    return ReportResponse(**report)
