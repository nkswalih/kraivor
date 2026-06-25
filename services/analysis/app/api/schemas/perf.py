from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class PerformanceMetricResponse(BaseModel):
    id: UUID
    metric_type: str
    endpoint: Optional[str] = None
    http_method: Optional[str] = None
    estimated_rpm: Optional[int] = None
    p50_latency_ms: Optional[int] = None
    p95_latency_ms: Optional[int] = None
    p99_latency_ms: Optional[int] = None
    bottleneck_type: Optional[str] = None
    bottleneck_severity: Optional[str] = None


class PerformanceMetricListResponse(BaseModel):
    metrics: list[PerformanceMetricResponse]
    total: int
