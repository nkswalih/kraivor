from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class StartAnalysisRequest(BaseModel):
    repo_id: UUID
    workspace_id: UUID
    repo_url: str
    branch: str = "main"
    deep_scan: bool = False
    depth: int = Field(default=1, ge=1, le=10)


class JobStatusResponse(BaseModel):
    job_id: str
    repo_id: UUID
    workspace_id: UUID
    status: str
    repo_url: str
    branch: str = "main"
    progress_pct: float = 0.0
    progress_message: str = ""
    total_findings: int = 0
    total_files: Optional[int] = None
    total_lines: Optional[int] = None
    overall_score: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    jobs: list[JobStatusResponse]
    total: int
    page: int
    page_size: int
