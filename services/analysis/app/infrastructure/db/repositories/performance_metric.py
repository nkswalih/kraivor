from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.performance_metric import PerformanceMetricModel


class PerformanceMetricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, entries: list[dict]) -> int:
        models = [PerformanceMetricModel(**e) for e in entries]
        self._session.add_all(models)
        await self._session.flush()
        return len(models)

    async def get_by_job(self, job_id: UUID) -> list[dict]:
        stmt = select(PerformanceMetricModel).where(
            PerformanceMetricModel.job_id == job_id
        )
        result = await self._session.execute(stmt)
        return [
            {
                "id": m.id,
                "metric_type": m.metric_type,
                "endpoint": m.endpoint,
                "http_method": m.http_method,
                "estimated_rpm": m.estimated_rpm,
                "p50_latency_ms": m.p50_latency_ms,
                "p95_latency_ms": m.p95_latency_ms,
                "p99_latency_ms": m.p99_latency_ms,
                "bottleneck_type": m.bottleneck_type,
                "bottleneck_severity": m.bottleneck_severity,
            }
            for m in result.scalars().all()
        ]
