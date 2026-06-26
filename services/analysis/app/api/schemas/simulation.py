from uuid import UUID

from pydantic import BaseModel


class SimulationResultResponse(BaseModel):
    id: UUID
    concurrent_users: int
    status: str
    overall_rpm: int | None = None
    error_rate_pct: float | None = None
    endpoints_analysis: object | None = None
    bottlenecks: list[object] | None = None


class SimulationResultListResponse(BaseModel):
    results: list[SimulationResultResponse]
    total: int
