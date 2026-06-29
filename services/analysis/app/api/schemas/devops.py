from uuid import UUID

from pydantic import BaseModel


class DevOpsFindingResponse(BaseModel):
    id: UUID
    devops_type: str
    category: str
    severity: str
    title: str
    description: str | None = None
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    recommendation: str | None = None
    confidence: float = 0.8
    devops_score: dict | None = None


class DevOpsFindingListResponse(BaseModel):
    findings: list[DevOpsFindingResponse]
    total: int
