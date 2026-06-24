from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReportResponse(BaseModel):
    report_id: str
    job_id: str
    overall_score: float
    findings_count: int
    summary: str
    breakdown: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    report_url: Optional[str] = None
