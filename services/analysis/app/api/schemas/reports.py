from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReportResponse(BaseModel):
    job_id: UUID
    repo_id: UUID
    workspace_id: UUID
    branch: str = "main"
    overall_score: float | None = None
    performance_score: float | None = None
    security_score: float | None = None
    reliability_score: float | None = None
    maintainability_score: float | None = None
    devops_score: float | None = None
    total_findings: int = 0
    total_files: int = 0
    duration_seconds: int | None = None
    completed_at: datetime | None = None
    report_url: str | None = None
