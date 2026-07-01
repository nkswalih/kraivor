from dataclasses import dataclass
from uuid import UUID


@dataclass(kw_only=True)
class GetJobStatusQuery:
    job_id: UUID


@dataclass(kw_only=True)
class ListFindingsQuery:
    job_id: UUID
    category: str | None = None
    severity: str | None = None
    include_dismissed: bool = False
    limit: int = 100
    offset: int = 0


@dataclass(kw_only=True)
class DismissFindingsCommand:
    finding_ids: list[UUID]
    dismissed: bool = True


@dataclass(kw_only=True)
class GetFindingsSummaryQuery:
    job_id: UUID


@dataclass(kw_only=True)
class GetReportQuery:
    report_id: UUID | None = None
    job_id: UUID | None = None


@dataclass(kw_only=True)
class ListJobsQuery:
    repo_id: UUID | None = None
    workspace_id: UUID | None = None
    limit: int = 10
    offset: int = 0
