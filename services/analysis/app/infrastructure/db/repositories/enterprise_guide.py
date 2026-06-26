from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.enterprise_guide import EnterpriseGuideModel


class EnterpriseGuideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, guide: dict[str, object]) -> None:
        model = EnterpriseGuideModel(**guide)
        self._session.add(model)
        await self._session.flush()

    async def get_by_job(self, job_id: UUID) -> dict[str, object] | None:
        stmt = select(EnterpriseGuideModel).where(
            EnterpriseGuideModel.job_id == job_id
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return None
        return {
            "id": m.id,
            "job_id": m.job_id,
            "executive_summary": m.executive_summary,
            "critical_issues": m.critical_issues,
            "high_issues": m.high_issues,
            "medium_issues": m.medium_issues,
            "architecture_review": m.architecture_review,
            "capacity_analysis": m.capacity_analysis,
            "migration_path": m.migration_path,
            "generated_at": m.generated_at,
        }
