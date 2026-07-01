from uuid import UUID

from pydantic import BaseModel


class MaintainabilityFindingResponse(BaseModel):
    id: UUID
    maintainability_type: str
    severity: str
    title: str
    description: str | None = None
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    recommendation: str | None = None
    confidence: float = 0.8
    estimated_effort_hours: float | None = None


class MaintainabilityFindingListResponse(BaseModel):
    findings: list[MaintainabilityFindingResponse]
    total: int


class MaintainabilityMetricsResponse(BaseModel):
    maintainability_index: float = 100.0
    technical_debt_hours: float = 0.0
    complexity_score: float = 100.0
    total_findings: int = 0
