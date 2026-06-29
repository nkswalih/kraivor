from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.finding import Finding
from app.domain.entities.report import Report
from app.domain.entities.score import Score


class AbstractJobRepository(ABC):
    """Contract for analysis job persistence."""

    @abstractmethod
    async def create(self, job_data: dict[str, object]) -> dict[str, object]:
        ...

    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> dict[str, object] | None:
        ...

    @abstractmethod
    async def update_status(
        self, job_id: UUID, status: str, progress_pct: int = 0, **kwargs: object
    ) -> None:
        ...

    @abstractmethod
    async def list_by_repo(
        self, repo_id: UUID, limit: int = 10, offset: int = 0
    ) -> tuple[list[dict[str, object]], int]:
        ...

    @abstractmethod
    async def list_by_workspace(
        self, workspace_id: UUID, limit: int = 10, offset: int = 0
    ) -> tuple[list[dict[str, object]], int]:
        ...


class AbstractFindingRepository(ABC):
    """Contract for finding persistence."""

    @abstractmethod
    async def save_many(self, findings: list[Finding]) -> int:
        """Save findings in batch. Returns count saved."""
        ...

    @abstractmethod
    async def get_by_job(
        self,
        job_id: UUID,
        category: str | None = None,
        severity: str | None = None,
        include_dismissed: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Finding], int]:
        """Get findings for a job with optional filters. Returns (findings, total_count).

        When ``include_dismissed`` is ``False`` (default) only ``ACTIVE`` findings are
        returned. Pass ``True`` to include dismissed findings as well.
        """
        ...

    @abstractmethod
    async def get_by_repo(
        self,
        repo_id: UUID,
        category: str | None = None,
        severity: str | None = None,
        include_dismissed: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Finding], int]:
        """Get findings for a repo with optional filters."""
        ...

    @abstractmethod
    async def dismiss(self, finding_id: UUID) -> None:
        """Mark a single finding as dismissed."""
        ...

    @abstractmethod
    async def dismiss_many(self, finding_ids: list[UUID]) -> int:
        """Mark findings as dismissed in batch. Returns count updated."""
        ...

    @abstractmethod
    async def count_by_severity(self, job_id: UUID) -> dict[str, int]:
        """Count findings grouped by severity for a job."""
        ...

    @abstractmethod
    async def count_by_category(self, job_id: UUID) -> dict[str, int]:
        """Count findings grouped by category for a job."""
        ...


class AbstractReportRepository(ABC):
    """Contract for report persistence."""

    @abstractmethod
    async def save(self, report: Report) -> None:
        ...

    @abstractmethod
    async def get_by_job(self, job_id: UUID) -> Report | None:
        ...

    @abstractmethod
    async def get_latest_by_repo(
        self, repo_id: UUID
    ) -> tuple[Report | None, Score | None]:
        """Get the most recent report and score for a repo."""
        ...
