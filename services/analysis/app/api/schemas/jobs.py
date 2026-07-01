from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StartAnalysisRequest(BaseModel):
    repo_id: UUID
    workspace_id: UUID
    repo_url: str
    branch: str = "main"
    deep_scan: bool = False
    depth: int = Field(default=1, ge=1, le=10)


class EngineStatusEntry(BaseModel):
    engine: str
    status: str
    reason: str = ""
    error_code: str = ""


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
    total_files: int | None = None
    total_lines: int | None = None
    overall_score: int | None = None
    blocked_by: list[str] = []
    engine_statuses: dict[str, str] = {}
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobListResponse(BaseModel):
    jobs: list[JobStatusResponse]
    total: int
    page: int
    page_size: int
