from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.analysis_metadata import AnalysisMetadata
from app.infrastructure.db.models.analysis_metadata import AnalysisMetadataModel


class AnalysisMetadataRepository:
    """SQLAlchemy implementation for analysis_metadata persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, metadata: AnalysisMetadata) -> None:
        """Insert or update the one metadata row belonging to this job.

        An upsert rather than a plain insert because parse now persists partial
        totals as it works, so a job is saved repeatedly. `get_by_job` reads
        with `scalar_one_or_none`, so a second insert would turn every later read
        into a `MultipleResultsFound`.

        `job_id` is the natural key. There is no unique constraint on it and
        none is needed here, because the pipeline runs one job at a time in a
        single worker; update-then-insert is therefore not racy in practice. It
        is preferred over `ON CONFLICT` so the statement also runs on SQLite.
        """
        stmt = (
            update(AnalysisMetadataModel)
            .where(AnalysisMetadataModel.job_id == metadata.job_id)
            .values(
                class_count=metadata.class_count,
                function_count=metadata.function_count,
                endpoint_count=metadata.endpoint_count,
                languages=metadata.languages,
                frameworks=metadata.frameworks,
                updated_at=datetime.now(),
            )
        )
        result = await self._session.execute(stmt)
        # AsyncSession.execute is declared as returning the base Result, which
        # has no rowcount. An UPDATE against a real dialect always yields a
        # CursorResult, empty-tuple-typed because an UPDATE returns no rows; the
        # cast is only there because the signature is wider than what comes back.
        if cast(CursorResult[()], result).rowcount:
            return

        self._session.add(
            AnalysisMetadataModel(
                id=metadata.id,
                job_id=metadata.job_id,
                class_count=metadata.class_count,
                function_count=metadata.function_count,
                endpoint_count=metadata.endpoint_count,
                languages=metadata.languages,
                frameworks=metadata.frameworks,
            )
        )

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
