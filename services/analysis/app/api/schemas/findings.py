from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class FindingResponse(BaseModel):
    finding_id: str
    job_id: str
    category: str
    severity: str
    message: str
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    rule_id: str = ""
    code_snippet: str = ""
    created_at: datetime


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
