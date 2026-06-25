from uuid import UUID

from pydantic import BaseModel


class PerformanceMetricResponse(BaseModel):
    id: UUID
    metric_type: str
    endpoint: str | None = None
    http_method: str | None = None
    estimated_rpm: int | None = None
    p50_latency_ms: int | None = None
    p95_latency_ms: int | None = None
    p99_latency_ms: int | None = None
    bottleneck_type: str | None = None
    bottleneck_severity: str | None = None


class PerformanceMetricListResponse(BaseModel):
    metrics: list[PerformanceMetricResponse]
    total: int
