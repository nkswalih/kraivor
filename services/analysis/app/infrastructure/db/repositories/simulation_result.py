from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.simulation_result import SimulationResultModel


class SimulationResultRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, entries: list[dict[str, object]]) -> int:
        models = [SimulationResultModel(**e) for e in entries]
        self._session.add_all(models)
        await self._session.flush()
        return len(models)

    async def get_by_job(self, job_id: UUID) -> list[dict[str, object]]:
        stmt = select(SimulationResultModel).where(
            SimulationResultModel.job_id == job_id
        )
        result = await self._session.execute(stmt)
        return [
            {
                "id": m.id,
                "concurrent_users": m.concurrent_users,
                "status": m.status,
                "overall_rpm": m.overall_rpm,
                "error_rate_pct": m.error_rate_pct,
                "endpoints_analysis": m.endpoints_analysis,
                "bottlenecks": m.bottlenecks,
            }
            for m in result.scalars().all()
        ]

    async def count_by_job(self, job_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(SimulationResultModel)
            .where(SimulationResultModel.job_id == job_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0
