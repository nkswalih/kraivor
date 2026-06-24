from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.contracts.repository_provider import AbstractReportRepository
from app.domain.entities.report import Report
from app.domain.entities.score import Score
from app.infrastructure.db.models.analysis_job import AnalysisJobModel
from app.infrastructure.db.models.enterprise_guide import EnterpriseGuideModel


class ReportRepository(AbstractReportRepository):
    """SQLAlchemy implementation of AbstractReportRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: Report) -> None:
        # Reports are derived from analysis_jobs and enterprise_guides
        # We save via the job and guide models
        pass

    async def get_by_job(self, job_id: UUID) -> Report | None:
        stmt = select(AnalysisJobModel).where(AnalysisJobModel.id == job_id)
        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            return None

        return self._build_report(job)

    async def get_latest_by_repo(
        self, repo_id: UUID
    ) -> tuple[Report | None, Score | None]:
        stmt = (
            select(AnalysisJobModel)
            .where(
                AnalysisJobModel.repo_id == repo_id,
                AnalysisJobModel.status == "completed",
            )
            .order_by(AnalysisJobModel.completed_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        job = result.scalar_one_or_none()
        if not job:
            return None, None

        report = self._build_report(job)
        score = None
        if job.overall_score is not None:
            score = Score(
                overall=job.overall_score,
                performance=job.performance_score or 100,
                security=job.security_score or 100,
                reliability=job.reliability_score or 100,
                maintainability=job.maintainability_score or 100,
                devops=job.devops_score or 100,
                findings_count=job.total_findings,
                critical_count=job.critical_count,
                high_count=job.high_count,
                medium_count=job.medium_count,
                low_count=job.low_count,
            )

        return report, score

    def _build_report(self, job: AnalysisJobModel) -> Report:
        return Report(
            job_id=job.id,
            repo_id=job.repo_id,
            workspace_id=job.workspace_id,
            branch=job.branch,
            duration_seconds=job.duration_seconds,
            completed_at=job.completed_at,
        )
