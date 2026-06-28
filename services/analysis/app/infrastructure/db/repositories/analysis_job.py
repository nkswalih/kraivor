from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.contracts.repository_provider import AbstractJobRepository
from app.infrastructure.db.models.analysis_job import AnalysisJobModel


class JobRepository(AbstractJobRepository):
    """SQLAlchemy implementation of AbstractJobRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, job_data: dict[str, object]) -> dict[str, object]:
        model = AnalysisJobModel(**job_data)
        self._session.add(model)
        await self._session.flush()
        return self._to_dict(model)

    async def get_by_id(self, job_id: UUID) -> dict[str, object] | None:
        stmt = select(AnalysisJobModel).where(
            AnalysisJobModel.id == job_id,
            AnalysisJobModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_dict(model) if model else None

    async def update_status(
        self, job_id: UUID, status: str, progress_pct: int = 0, **kwargs: object
    ) -> None:
        values = {"status": status, "progress_pct": progress_pct, **kwargs}
        stmt = (
            update(AnalysisJobModel)
            .where(AnalysisJobModel.id == job_id)
            .values(**values)
        )
        await self._session.execute(stmt)

    async def list_by_repo(
        self, repo_id: UUID, limit: int = 10, offset: int = 0
    ) -> tuple[list[dict[str, object]], int]:
        base = select(AnalysisJobModel).where(
            AnalysisJobModel.repo_id == repo_id,
            AnalysisJobModel.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = base.order_by(AnalysisJobModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_dict(m) for m in result.scalars().all()], total

    async def list_by_workspace(
        self, workspace_id: UUID, limit: int = 10, offset: int = 0
    ) -> tuple[list[dict[str, object]], int]:
        base = select(AnalysisJobModel).where(
            AnalysisJobModel.workspace_id == workspace_id,
            AnalysisJobModel.deleted_at.is_(None),
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = base.order_by(AnalysisJobModel.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_dict(m) for m in result.scalars().all()], total

    async def count_by_workspace(self, workspace_id: UUID) -> int:
        stmt = select(func.count()).select_from(AnalysisJobModel).where(
            AnalysisJobModel.workspace_id == workspace_id,
            AnalysisJobModel.deleted_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    @staticmethod
    def _to_dict(model: AnalysisJobModel) -> dict[str, object]:
        return {
            "id": model.id,
            "repo_id": model.repo_id,
            "workspace_id": model.workspace_id,
            "triggered_by": model.triggered_by,
            "trigger_type": model.trigger_type,
            "repo_url": model.repo_url,
            "branch": model.branch,
            "deep_scan": model.deep_scan,
            "simulate_users": model.simulate_users,
            "status": model.status,
            "progress_pct": model.progress_pct,
            "progress_message": model.progress_message,
            "total_files": model.total_files,
            "total_lines": model.total_lines,
            "total_findings": model.total_findings,
            "critical_count": model.critical_count,
            "high_count": model.high_count,
            "medium_count": model.medium_count,
            "low_count": model.low_count,
            "overall_score": model.overall_score,
            "error_message": model.error_message,
            "started_at": model.started_at.isoformat() if model.started_at else None,
            "completed_at": model.completed_at.isoformat() if model.completed_at else None,
            "duration_seconds": model.duration_seconds,
            "created_at": model.created_at.isoformat() if model.created_at else None,
        }
