from uuid import UUID

from pydantic import BaseModel


class ReliabilityFindingResponse(BaseModel):
    id: UUID
    reliability_type: str
    severity: str
    title: str
    description: str | None = None
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    recommendation: str | None = None
    confidence: float = 0.8


class ReliabilityFindingListResponse(BaseModel):
    findings: list[ReliabilityFindingResponse]
    total: int
