from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.enterprise_guide import EnterpriseGuideModel


class EnterpriseGuideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, guide: dict[str, object]) -> None:
        model = EnterpriseGuideModel(**guide)
        model = await self._session.merge(model)
        await self._session.flush()

    async def get_by_job(self, job_id: UUID) -> dict[str, object] | None:
        stmt = select(EnterpriseGuideModel).where(EnterpriseGuideModel.job_id == job_id)
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        if not m:
            return None
        return {
            "id": m.id,
            "job_id": m.job_id,
            "repo_id": m.repo_id,
            "workspace_id": m.workspace_id,
            "executive_summary": m.executive_summary,
            "critical_issues": m.critical_issues,
            "high_issues": m.high_issues,
            "medium_issues": m.medium_issues,
            "architecture_review": m.architecture_review,
            "capacity_analysis": m.capacity_analysis,
            "migration_path": m.migration_path,
            "ai_executive_summary": m.ai_executive_summary,
            "repository_health": m.repository_health,
            "engineering_scorecard": m.engineering_scorecard,
            "business_risk": m.business_risk,
            "scalability_review": m.scalability_review,
            "technical_debt": m.technical_debt,
            "issue_clusters": m.issue_clusters,
            "hotspots": m.hotspots,
            "service_health": m.service_health,
            "quick_wins": m.quick_wins,
            "sprint_roadmap": m.sprint_roadmap,
            "deployment_readiness": m.deployment_readiness,
            "release_recommendation": m.release_recommendation,
            "ownership": m.ownership,
            "estimated_effort": m.estimated_effort,
            "ai_recommendations": m.ai_recommendations,
            "raw_findings": m.raw_findings,
            "generated_at": m.generated_at,
        }

    async def exists_by_job(self, job_id: UUID) -> bool:
        stmt = (
            select(func.count())
            .select_from(EnterpriseGuideModel)
            .where(EnterpriseGuideModel.job_id == job_id)
        )
        result = await self._session.execute(stmt)
        return (result.scalar() or 0) > 0
