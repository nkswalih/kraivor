from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.file_analysis import FileAnalysisModel


class FileAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, entries: list[dict[str, object]]) -> int:
        models = [FileAnalysisModel(**e) for e in entries]
        self._session.add_all(models)
        await self._session.flush()
        return len(models)

    async def get_by_job(self, job_id: UUID) -> list[dict[str, object]]:
        stmt = select(FileAnalysisModel).where(FileAnalysisModel.job_id == job_id)
        result = await self._session.execute(stmt)
        return [
            {
                "id": m.id,
                "original_filename": m.original_filename,
                "file_size_bytes": m.file_size_bytes,
                "language": m.language,
                "findings_count": m.findings_count,
                "s3_key": m.s3_key,
            }
            for m in result.scalars().all()
        ]
