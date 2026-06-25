from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass(kw_only=True)
class Repository:
    """Value object representing a repository for analysis."""

    id: UUID
    workspace_id: UUID
    clone_url: str
    branch: str = "main"
    name: str = ""
    languages: list[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0
    file_tree: dict[str, list[dict]] = field(default_factory=dict)
    analyzed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
