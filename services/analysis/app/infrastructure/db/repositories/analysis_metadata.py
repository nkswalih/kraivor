from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.analysis_metadata import AnalysisMetadata
from app.infrastructure.db.models.analysis_metadata import AnalysisMetadataModel


class AnalysisMetadataRepository:
    """SQLAlchemy implementation for analysis_metadata persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, metadata: AnalysisMetadata) -> None:
        model = AnalysisMetadataModel(
            id=metadata.id,
            job_id=metadata.job_id,
            class_count=metadata.class_count,
            function_count=metadata.function_count,
            endpoint_count=metadata.endpoint_count,
            languages=metadata.languages,
            frameworks=metadata.frameworks,
        )
        self._session.add(model)

    async def get_by_job(self, job_id: UUID) -> AnalysisMetadata | None:
        stmt = select(AnalysisMetadataModel).where(
            AnalysisMetadataModel.job_id == job_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return self._to_entity(model)

    def _to_entity(self, model: AnalysisMetadataModel) -> AnalysisMetadata:
        return AnalysisMetadata(
            id=model.id,
            job_id=model.job_id,
            class_count=model.class_count,
            function_count=model.function_count,
            endpoint_count=model.endpoint_count,
            languages=model.languages or [],
            frameworks=model.frameworks or [],
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
