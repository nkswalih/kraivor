from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SimulationResultResponse(BaseModel):
    id: UUID
    concurrent_users: int
    status: str
    overall_rpm: int | None = None
    error_rate_pct: float | None = None
    endpoints_analysis: Any | None = None
    bottlenecks: list | None = None


class SimulationResultListResponse(BaseModel):
    results: list[SimulationResultResponse]
    total: int
