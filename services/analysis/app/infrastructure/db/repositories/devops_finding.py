from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.devops_finding import DevOpsFindingModel


class DevOpsFindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, entries: list[dict[str, object]]) -> int:
        models = [DevOpsFindingModel(**e) for e in entries]
        self._session.add_all(models)
        await self._session.flush()
        return len(models)

    async def get_by_job(self, job_id: UUID) -> list[dict[str, object]]:
        stmt = select(DevOpsFindingModel).where(DevOpsFindingModel.job_id == job_id)
        result = await self._session.execute(stmt)
        return [
            {
                "id": m.id,
                "devops_type": m.devops_type,
                "category": m.category,
                "severity": m.severity,
                "title": m.title,
                "description": m.description,
                "file_path": m.file_path,
                "line_start": m.line_start,
                "line_end": m.line_end,
                "code_snippet": m.code_snippet,
                "recommendation": m.recommendation,
                "confidence": m.confidence,
                "devops_score": m.devops_score,
            }
            for m in result.scalars().all()
        ]
