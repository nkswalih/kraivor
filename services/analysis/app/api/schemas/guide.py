from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EnterpriseGuideResponse(BaseModel):
    id: UUID
    job_id: UUID
    executive_summary: str | None = None
    critical_issues: list | None = None
    high_issues: list | None = None
    medium_issues: list | None = None
    architecture_review: dict[str, Any] | None = None
    capacity_analysis: dict[str, Any] | None = None
    migration_path: list | None = None
    generated_at: datetime | None = None
