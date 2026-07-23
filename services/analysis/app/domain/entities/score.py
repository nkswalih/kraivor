from dataclasses import dataclass, field

from app.core.constants import SCORE_TIER_THRESHOLDS, Tiers


@dataclass(kw_only=True)
class Score:
    """Value object representing a production readiness score.

    Five dimensions with configurable weights.
    A category score of ``None`` means the module has no data
    (e.g. devops rules are not implemented) and should be
    rendered as ``None`` (N/A) rather than defaulting to 100.

    ``overall`` is ``None`` when a **blocked** state is detected:
    a core engine (security, maintainability) failed or was not
    configured.  ``blocked_by`` lists the engine IDs that caused
    the blockage along with their failure reason.
    """

    overall: int | None = None
    performance: int | None = None
    security: int | None = None
    reliability: int | None = None
    maintainability: int | None = None
    devops: int | None = None

    blocked_by: list[str] = field(default_factory=list)
    engine_statuses: dict[str, str] = field(default_factory=dict)

    findings_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    def __post_init__(self) -> None:
        self._tier = self._compute_tier()

    def _compute_tier(self) -> Tiers | None:
        if self.overall is None:
            return None
        for threshold, tier in SCORE_TIER_THRESHOLDS:
            if self.overall >= threshold:
                return tier
        return Tiers.CRITICAL_STATE

    @property
    def tier(self) -> Tiers | None:
        return self._tier

    @property
    def is_blocked(self) -> bool:
        return self.overall is None

    def to_dict(self) -> dict[str, object]:
        return {
            "overall": self.overall,
            "performance": self.performance,
            "security": self.security,
            "reliability": self.reliability,
            "maintainability": self.maintainability,
            "devops": self.devops,
            "blocked_by": list(self.blocked_by),
            "engine_statuses": dict(self.engine_statuses),
            "tier": str(self.tier) if self.tier is not None else None,
            "findings_count": self.findings_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
        }
