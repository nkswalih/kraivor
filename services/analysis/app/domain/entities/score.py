from dataclasses import dataclass
from typing import Any

from app.core.constants import SCORE_TIER_THRESHOLDS, Tiers


@dataclass(kw_only=True)
class Score:
    """Value object representing a production readiness score.

    Five dimensions with configurable weights:
    - Performance (25%)
    - Security (25%)
    - Reliability (20%)
    - Maintainability (15%)
    - DevOps (15%)
    """

    overall: int
    performance: int = 100
    security: int = 100
    reliability: int = 100
    maintainability: int = 100
    devops: int = 100

    findings_count: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    def __post_init__(self) -> None:
        self._tier = self._compute_tier()

    def _compute_tier(self) -> Tiers:
        for threshold, tier in SCORE_TIER_THRESHOLDS:
            if self.overall >= threshold:
                return tier
        return Tiers.CRITICAL_STATE

    @property
    def tier(self) -> Tiers:
        return self._tier

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall": self.overall,
            "performance": self.performance,
            "security": self.security,
            "reliability": self.reliability,
            "maintainability": self.maintainability,
            "devops": self.devops,
            "tier": str(self.tier),
            "findings_count": self.findings_count,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
        }
