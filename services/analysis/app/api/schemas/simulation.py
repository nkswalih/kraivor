from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class SimulationResultResponse(BaseModel):
    id: UUID
    concurrent_users: int
    status: str
    overall_rpm: Optional[int] = None
    error_rate_pct: Optional[float] = None
    endpoints_analysis: Optional[Any] = None
    bottlenecks: Optional[list] = None


class SimulationResultListResponse(BaseModel):
    results: list[SimulationResultResponse]
    total: int
