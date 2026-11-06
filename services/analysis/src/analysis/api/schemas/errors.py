from uuid import UUID

from pydantic import BaseModel


class ErrorFindingResponse(BaseModel):
    id: UUID
    error_type: str
    severity: str
    title: str
    description: str | None = None
    file_path: str
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str | None = None
    recommendation: str | None = None


class ErrorFindingListResponse(BaseModel):
    findings: list[ErrorFindingResponse]
    total: int
