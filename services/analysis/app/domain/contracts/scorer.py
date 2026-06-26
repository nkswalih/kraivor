from abc import ABC, abstractmethod
from dataclasses import dataclass

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


class AbstractScorer(ABC):
    """Contract for score calculation engines."""

    @abstractmethod
    def calculate(
        self,
        violations: list[Violation],
        weights: dict[str, float] | None = None,
    ) -> Score:
        """Calculate production readiness score from violations."""
