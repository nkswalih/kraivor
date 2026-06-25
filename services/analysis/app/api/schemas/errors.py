from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ErrorFindingResponse(BaseModel):
    id: UUID
    error_type: str
    severity: str
    title: str
    description: Optional[str] = None
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: Optional[str] = None
    recommendation: Optional[str] = None


class ErrorFindingListResponse(BaseModel):
    findings: list[ErrorFindingResponse]
    total: int
