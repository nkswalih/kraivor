from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.maintainability_finding import MaintainabilityFindingModel


class MaintainabilityFindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, entries: list[dict[str, object]]) -> int:
        models = [MaintainabilityFindingModel(**e) for e in entries]
        self._session.add_all(models)
        await self._session.flush()
        return len(models)

    async def get_by_job(self, job_id: UUID) -> list[dict[str, object]]:
        stmt = select(MaintainabilityFindingModel).where(MaintainabilityFindingModel.job_id == job_id)
        result = await self._session.execute(stmt)
        return [
            {
                "id": m.id,
                "maintainability_type": m.maintainability_type,
                "severity": m.severity,
                "title": m.title,
                "description": m.description,
                "file_path": m.file_path,
                "line_start": m.line_start,
                "line_end": m.line_end,
                "code_snippet": m.code_snippet,
                "recommendation": m.recommendation,
                "confidence": m.confidence,
                "estimated_effort_hours": m.estimated_effort_hours,
            }
            for m in result.scalars().all()
        ]

    async def get_metrics_by_job(self, job_id: UUID) -> dict[str, object] | None:
        stmt = select(MaintainabilityFindingModel.metrics).where(
            MaintainabilityFindingModel.job_id == job_id
        ).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None:
            return dict(row) if isinstance(row, dict) else None
        return None
