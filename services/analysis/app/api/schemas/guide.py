from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EnterpriseGuideResponse(BaseModel):
    id: UUID
    job_id: UUID
    executive_summary: str | None = None
    critical_issues: list[object] | None = None
    high_issues: list[object] | None = None
    medium_issues: list[object] | None = None
    architecture_review: dict[str, object] | None = None
    capacity_analysis: dict[str, object] | None = None
    migration_path: list[object] | None = None
    generated_at: datetime | None = None
    ai_executive_summary: str | None = None
