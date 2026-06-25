from uuid import UUID

from pydantic import BaseModel


class DeadCodeFindingResponse(BaseModel):
    id: UUID
    code_type: str
    name: str
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    context: str | None = None
    evidence: str | None = None
    confidence: float = 0.0


class DeadCodeListResponse(BaseModel):
    findings: list[DeadCodeFindingResponse]
    total: int
