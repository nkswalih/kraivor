from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.analysis_job import JobRepository
from app.infrastructure.db.repositories.dead_code import DeadCodeRepository
from app.infrastructure.db.repositories.enterprise_guide import (
    EnterpriseGuideRepository,
)
from app.infrastructure.db.repositories.error_finding import ErrorFindingRepository
from app.infrastructure.db.repositories.file_analysis import FileAnalysisRepository
from app.infrastructure.db.repositories.finding import FindingRepository
from app.infrastructure.db.repositories.performance_metric import (
    PerformanceMetricRepository,
)
from app.infrastructure.db.repositories.report import ReportRepository
from app.infrastructure.db.repositories.score_history import ScoreHistoryRepository
from app.infrastructure.db.repositories.simulation_result import (
    SimulationResultRepository,
)
from app.infrastructure.db.session import async_session_factory


class UnitOfWork:
    """Transaction boundary for analysis operations.

    Wraps multiple repository operations in a single database transaction.
    Either all succeed or all roll back.

    Usage:
        async with UnitOfWork() as uow:
            await uow.jobs.create(data)
            await uow.findings.save_many(findings)
            await uow.commit()
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session
        self._external_session = session is not None
        self.jobs: JobRepository
        self.findings: FindingRepository
        self.reports: ReportRepository
        self.dead_code: DeadCodeRepository
        self.error_findings: ErrorFindingRepository
        self.performance_metrics: PerformanceMetricRepository
        self.simulation_results: SimulationResultRepository
        self.score_history: ScoreHistoryRepository
        self.enterprise_guides: EnterpriseGuideRepository
        self.file_analyses: FileAnalysisRepository

    async def __aenter__(self) -> "UnitOfWork":
        if self._session is None:
            self._session = async_session_factory()
        self.jobs = JobRepository(self._session)
        self.findings = FindingRepository(self._session)
        self.reports = ReportRepository(self._session)
        self.dead_code = DeadCodeRepository(self._session)
        self.error_findings = ErrorFindingRepository(self._session)
        self.performance_metrics = PerformanceMetricRepository(self._session)
        self.simulation_results = SimulationResultRepository(self._session)
        self.score_history = ScoreHistoryRepository(self._session)
        self.enterprise_guides = EnterpriseGuideRepository(self._session)
        self.file_analyses = FileAnalysisRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            if not self._external_session:
                await self._session.close()

    async def commit(self) -> None:
        """Explicitly commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        return self._session
