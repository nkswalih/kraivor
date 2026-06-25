from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class EnterpriseGuideResponse(BaseModel):
    id: UUID
    job_id: UUID
    executive_summary: Optional[str] = None
    critical_issues: Optional[list] = None
    high_issues: Optional[list] = None
    medium_issues: Optional[list] = None
    architecture_review: Optional[dict[str, Any]] = None
    capacity_analysis: Optional[dict[str, Any]] = None
    migration_path: Optional[list] = None
    generated_at: Optional[datetime] = None
