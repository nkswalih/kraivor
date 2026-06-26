from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.dead_code import DeadCodeModel


class DeadCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, entries: list[dict[str, object]]) -> int:
        models = [DeadCodeModel(**e) for e in entries]
        self._session.add_all(models)
        await self._session.flush()
        return len(models)

    async def get_by_job(self, job_id: UUID) -> list[dict[str, object]]:
        stmt = select(DeadCodeModel).where(DeadCodeModel.job_id == job_id)
        result = await self._session.execute(stmt)
        return [
            {
                "id": m.id,
                "code_type": m.code_type,
                "name": m.name,
                "file_path": m.file_path,
                "line_start": m.line_start,
                "line_end": m.line_end,
                "context": m.context,
                "evidence": m.evidence,
                "confidence": m.confidence,
            }
            for m in result.scalars().all()
        ]
