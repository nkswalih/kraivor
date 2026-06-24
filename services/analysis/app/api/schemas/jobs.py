from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class StartAnalysisRequest(BaseModel):
    repo_url: str
    branch: str = "main"
    depth: int = Field(default=1, ge=1, le=10)


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    repo_url: str
    branch: str = "main"
    progress_pct: float = 0.0
    progress_message: str = ""
    total_files: Optional[int] = None
    total_lines: Optional[int] = None
    languages: Optional[dict[str, int]] = None
    frameworks: list[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    jobs: list[JobStatusResponse]
    total: int
    page: int
    page_size: int
