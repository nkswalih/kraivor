from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DeadCodeFindingResponse(BaseModel):
    id: UUID
    code_type: str
    name: str
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    context: Optional[str] = None
    evidence: Optional[str] = None
    confidence: float = 0.0


class DeadCodeListResponse(BaseModel):
    findings: list[DeadCodeFindingResponse]
    total: int
