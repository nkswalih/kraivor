from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ScoreHistoryEntryResponse(BaseModel):
    time: datetime
    overall_score: int
    performance_score: int | None = None
    security_score: int | None = None
    reliability_score: int | None = None
    maintainability_score: int | None = None
    devops_score: int | None = None
    findings_count: int = 0


class ScoreHistoryListResponse(BaseModel):
    entries: list[ScoreHistoryEntryResponse]
    total: int
