from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.contracts.repository_provider import AbstractReportRepository
from app.domain.entities.report import Report
from app.domain.entities.score import Score
from app.infrastructure.db.models.analysis_job import AnalysisJobModel


class ReportRepository(AbstractReportRepository):
    """SQLAlchemy implementation of AbstractReportRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, report: Report) -> None:
        stmt = (
            update(AnalysisJobModel)
            .where(AnalysisJobModel.id == report.job_id)
            .values(
                total_files=report.total_files_analyzed,
                duration_seconds=report.duration_seconds,
                languages_detected=report.languages_detected,
                overall_score=report.scores.overall if report.scores else None,
                performance_score=report.scores.performance if report.scores else None,
                security_score=report.scores.security if report.scores else None,
                reliability_score=report.scores.reliability if report.scores else None,
                maintainability_score=report.scores.maintainability if report.scores else None,
                devops_score=report.scores.devops if report.scores else None,
                critical_count=report.scores.critical_count if report.scores else 0,
                high_count=report.scores.high_count if report.scores else 0,
                medium_count=report.scores.medium_count if report.scores else 0,
                low_count=report.scores.low_count if report.scores else 0,
                total_findings=report.scores.findings_count if report.scores else 0,
            )
        )
        await self._session.execute(stmt)

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
                performance=job.performance_score,
                security=job.security_score,
                reliability=job.reliability_score,
                maintainability=job.maintainability_score,
                devops=job.devops_score,
                findings_count=job.total_findings,
                critical_count=job.critical_count,
                high_count=job.high_count,
                medium_count=job.medium_count,
                low_count=job.low_count,
            )

        return report, score

    def _build_report(self, job: AnalysisJobModel) -> Report:
        score = None
        if job.overall_score is not None:
            score = Score(
                overall=job.overall_score,
                performance=job.performance_score,
                security=job.security_score,
                reliability=job.reliability_score,
                maintainability=job.maintainability_score,
                devops=job.devops_score,
                findings_count=job.total_findings,
                critical_count=job.critical_count,
                high_count=job.high_count,
                medium_count=job.medium_count,
                low_count=job.low_count,
            )
        languages: list[str] = []
        if job.languages_detected:
            languages = list(job.languages_detected)
        return Report(
            job_id=job.id,
            repo_id=job.repo_id,
            workspace_id=job.workspace_id,
            branch=job.branch,
            languages_detected=languages,
            duration_seconds=job.duration_seconds,
            completed_at=job.completed_at,  # type: ignore[arg-type]
            scores=score,
            total_files_analyzed=job.total_files or 0,
            total_lines_of_code=job.total_lines or 0,
        )
