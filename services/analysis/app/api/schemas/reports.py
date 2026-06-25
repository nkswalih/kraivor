from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReportResponse(BaseModel):
    job_id: UUID
    repo_id: UUID
    workspace_id: UUID
    branch: str = "main"
    overall_score: Optional[float] = None
    performance_score: Optional[float] = None
    security_score: Optional[float] = None
    reliability_score: Optional[float] = None
    maintainability_score: Optional[float] = None
    devops_score: Optional[float] = None
    total_findings: int = 0
    total_files: int = 0
    duration_seconds: Optional[int] = None
    completed_at: Optional[datetime] = None
    report_url: Optional[str] = None
