from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FindingResponse(BaseModel):
    id: UUID
    job_id: UUID
    rule_id: str = ""
    category: str
    severity: str
    title: str
    description: str = ""
    recommendation: str = ""
    enterprise_pattern: str = ""
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: str = ""
    score_impact: float = 0.0
    rpm_impact: int = 0
    is_ai_enriched: bool = False


class FindingsListResponse(BaseModel):
    findings: list[FindingResponse]
    total: int
    page: int
    page_size: int


class FindingsSummaryResponse(BaseModel):
    job_id: str
    total: int
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
