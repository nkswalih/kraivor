from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class AnalysisMetadata:
    id: UUID = field(default_factory=uuid4)
    job_id: UUID
    class_count: int = 0
    function_count: int = 0
    endpoint_count: int = 0
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
