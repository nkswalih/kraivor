from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.score_history import ScoreHistoryModel


class ScoreHistoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, entry: dict[str, object]) -> None:
        model = ScoreHistoryModel(**entry)
        self._session.add(model)
        await self._session.flush()

    async def get_by_repo(self, repo_id: UUID, limit: int = 50) -> list[dict[str, object]]:
        stmt = (
            select(ScoreHistoryModel)
            .where(ScoreHistoryModel.repo_id == repo_id)
            .order_by(ScoreHistoryModel.time.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            {
                "time": m.time,
                "overall_score": m.overall_score,
                "performance_score": m.performance_score,
                "security_score": m.security_score,
                "reliability_score": m.reliability_score,
                "maintainability_score": m.maintainability_score,
                "devops_score": m.devops_score,
                "findings_count": m.findings_count,
            }
            for m in result.scalars().all()
        ]
