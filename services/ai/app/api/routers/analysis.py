from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies.auth import JWTPayload, get_current_user
from app.application.analysis.enrichment import EnrichmentService

CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]

router = APIRouter(tags=["analysis"])

_enrichment_service: EnrichmentService | None = None


def _get_enrichment() -> EnrichmentService:
    global _enrichment_service
    if _enrichment_service is None:
        _enrichment_service = EnrichmentService()
    return _enrichment_service


class EnrichFindingItem(BaseModel):
    title: str = ""
    category: str = ""
    severity: str = ""
    description: str = ""
    recommendation: str = ""
    file_path: str = ""
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str = ""
    fix_snippet: str = ""


class EnrichRequest(BaseModel):
    findings: list[EnrichFindingItem]
    overall_score: int | None = None
    tier: str | None = None
    languages: list[str] | None = None
    frameworks: list[str] | None = None


class EnrichedFindingItem(BaseModel):
    title: str = ""
    category: str = ""
    severity: str = ""
    description: str = ""
    recommendation: str = ""
    file_path: str = ""
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str = ""
    fix_snippet: str = ""
    ai_explanation: str = ""
    ai_recommendation: str = ""
    is_ai_enriched: bool = False


class EnrichResponse(BaseModel):
    findings: list[EnrichedFindingItem]
    ai_executive_summary: str = ""


@router.post("/v1/analysis/enrich", response_model=EnrichResponse)
async def enrich_analysis(
    request: EnrichRequest,
    _user: CurrentUser,
) -> EnrichResponse:
    service = _get_enrichment()
    result = await service.enrich(
        findings=[f.model_dump() for f in request.findings],
        overall_score=request.overall_score,
        tier=request.tier,
        languages=request.languages,
        frameworks=request.frameworks,
    )
    return EnrichResponse(
        findings=[EnrichedFindingItem(**f) for f in result["findings"]],
        ai_executive_summary=result.get("ai_executive_summary", ""),
    )
