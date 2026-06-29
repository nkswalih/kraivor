from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.domain.entities.score import Score


@dataclass(kw_only=True)
class Violation:
    """A rule violation produced by analysis rules.

    This is the output contract between rules and the scorer.
    Rules produce Violations; the scorer aggregates them into Scores.
    """

    rule_id: str
    category: str
    severity: str
    title: str
    description: str = ""
    file_path: str = ""
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str = ""
    recommendation: str = ""
    enterprise_pattern: str = ""
    score_impact: float = 0.0
    rpm_impact: int = 0
    breaks_at_users: int | None = None


@dataclass
class CapacityMetrics:
    """Capacity / load-test results fed into scoring.

    When a simulation run produced data, ``has_data`` is True.
    If the module is unimplemented or skipped, ``has_data`` is
    False and the scorer should return None for performance.
    """

    has_data: bool = False
    simulation_status: str | None = None   # "stable", "degraded", "failing"
    breaks_at_users: int | None = None
    overall_rpm: int | None = None
    bottlenecks: list[str] = field(default_factory=list)


class AbstractScorer(ABC):
    """Contract for score calculation engines."""

    @abstractmethod
    def calculate(
        self,
        violations: list[Violation],
        capacity: CapacityMetrics | None = None,
        engine_statuses: dict[str, str] | None = None,
        total_files: int = 0,
    ) -> Score:
        """Calculate production readiness score from violations and optional capacity data.

        ``engine_statuses`` maps engine IDs (e.g. ``"security"``,
        ``"devops"``) to their execution status (see ``EngineStatus``).
        When a core engine is ``failed`` or ``not_configured`` the
        overall score is ``None`` (blocked) and ``blocked_by`` lists
        the offending engine IDs.

        ``total_files`` is used for log-normalized per-rule scoring.
        A value of ``0`` (the default) falls back to linear penalties
        for backward compatibility.
        """
