from app.core.constants import SEVERITY_PENALTIES, Severity
from app.domain.contracts.scorer import AbstractScorer, Violation
from app.domain.entities.score import Score


class ProductionReadinessScorer(AbstractScorer):
    """Calculates production readiness scores from violations.

    Each category starts at 100. Violations deduct points based
    on severity and category weight. The overall score is a
    weighted average of all five categories.
    """

    CATEGORY_ORDER = [
        "performance",
        "security",
        "reliability",
        "maintainability",
        "devops",
    ]

    def calculate(
        self,
        violations: list[Violation],
        weights: dict[str, float] | None = None,
    ) -> Score:
        if weights is None:
            from app.core.config import get_settings

            settings = get_settings()
            weights = {
                "performance": settings.scoring.performance_weight,
                "security": settings.scoring.security_weight,
                "reliability": settings.scoring.reliability_weight,
                "maintainability": settings.scoring.maintainability_weight,
                "devops": settings.scoring.devops_weight,
            }

        category_scores: dict[str, float] = {cat: 100.0 for cat in self.CATEGORY_ORDER}
        severity_counts: dict[str, int] = {s.value: 0 for s in Severity}
        total_findings = len(violations)

        for v in violations:
            cat = v.category.lower()
            sev = v.severity.lower()

            if sev in severity_counts:
                severity_counts[sev] += 1

            if cat not in category_scores:
                continue

            try:
                sev_enum = Severity(sev)
                penalty = v.score_impact if v.score_impact else SEVERITY_PENALTIES.get(sev_enum, 0)
            except ValueError:
                penalty = v.score_impact or 0
            category_scores[cat] -= penalty

        for cat in category_scores:
            category_scores[cat] = max(0.0, category_scores[cat])

        overall = sum(
            category_scores[cat] * weights.get(cat, 0)
            for cat in self.CATEGORY_ORDER
        )
        overall = max(0, min(100, round(overall)))

        return Score(
            overall=overall,
            performance=max(0, min(100, round(category_scores["performance"]))),
            security=max(0, min(100, round(category_scores["security"]))),
            reliability=max(0, min(100, round(category_scores["reliability"]))),
            maintainability=max(0, min(100, round(category_scores["maintainability"]))),
            devops=max(0, min(100, round(category_scores["devops"]))),
            findings_count=total_findings,
            critical_count=severity_counts.get(Severity.CRITICAL.value, 0),
            high_count=severity_counts.get(Severity.HIGH.value, 0),
            medium_count=severity_counts.get(Severity.MEDIUM.value, 0),
            low_count=severity_counts.get(Severity.LOW.value, 0),
        )
