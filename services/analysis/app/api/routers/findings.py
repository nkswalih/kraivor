from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.services import get_uow
from app.api.schemas.findings import (
    DismissFindingsRequest,
    FindingResponse,
    FindingsListResponse,
    FindingsSummaryResponse,
)
from app.application.analysis.handler import (
    dismiss_findings,
    get_findings_summary,
    list_findings,
)
from app.application.analysis.queries import (
    DismissFindingsCommand,
    GetFindingsSummaryQuery,
    ListFindingsQuery,
)
from app.core.logging import get_logger
from app.dependencies.auth import JWTPayload, get_current_user
from app.domain.entities.finding import Finding
from app.infrastructure.db.unit_of_work import UnitOfWork

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])


@router.get("", response_model=FindingsListResponse)
async def list_findings_endpoint(
    job_id: UUID = Query(..., description="Filter by job ID"),
    severity: str | None = Query(None, description="Filter by severity"),
    category: str | None = Query(None, description="Filter by category"),
    include_dismissed: bool = Query(False, description="Include dismissed findings"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> FindingsListResponse:
    query = ListFindingsQuery(
        job_id=job_id,
        severity=severity,
        category=category,
        include_dismissed=include_dismissed,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    findings, total = await list_findings(query, uow)
    return FindingsListResponse(
        findings=[_finding_to_response(f) for f in findings],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/dismiss", status_code=status.HTTP_200_OK)
async def dismiss_findings_endpoint(
    body: DismissFindingsRequest,
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> dict[str, object]:
    if not body.finding_ids:
        raise HTTPException(status_code=400, detail="finding_ids must not be empty")

    command = DismissFindingsCommand(
        finding_ids=body.finding_ids, dismissed=body.dismissed
    )
    count = await dismiss_findings(command, uow)
    await uow.commit()
    return {"dismissed": count, "status": "ok"}


@router.get("/summary", response_model=FindingsSummaryResponse)
async def findings_summary(
    job_id: UUID = Query(..., description="Job ID"),
    uow: UnitOfWork = Depends(get_uow),
    _user: JWTPayload = Depends(get_current_user),
) -> FindingsSummaryResponse:
    query = GetFindingsSummaryQuery(job_id=job_id)
    result = await get_findings_summary(query, uow)
    by_severity = cast(dict[str, int], result.get("by_severity", {}))
    by_category = cast(dict[str, int], result.get("by_category", {}))
    total = sum(by_severity.values())
    return FindingsSummaryResponse(
        job_id=str(job_id),
        total=total,
        by_severity=by_severity,
        by_category=by_category,
    )


def _finding_to_response(f: Finding) -> FindingResponse:
    return FindingResponse(
        id=f.id,
        job_id=f.job_id,
        rule_id=f.rule_id,
        category=str(f.category),
        severity=str(f.severity),
        status=str(f.status),
        title=f.title,
        description=f.description or "",
        recommendation=f.recommendation or "",
        enterprise_pattern=f.enterprise_pattern or "",
        file_path=f.file_path or None,
        line_start=f.line_start,
        line_end=f.line_end,
        code_snippet=f.code_snippet or "",
        score_impact=f.score_impact or 0.0,
        rpm_impact=f.rpm_impact or 0,
        is_ai_enriched=f.is_ai_enriched,
        ai_explanation=f.ai_explanation or "",
    )
