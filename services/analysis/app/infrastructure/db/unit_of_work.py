from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repositories.analysis_job import JobRepository
from app.infrastructure.db.repositories.finding import FindingRepository
from app.infrastructure.db.repositories.report import ReportRepository
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

    async def __aenter__(self) -> "UnitOfWork":
        if self._session is None:
            self._session = async_session_factory()
        self.jobs = JobRepository(self._session)
        self.findings = FindingRepository(self._session)
        self.reports = ReportRepository(self._session)
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
