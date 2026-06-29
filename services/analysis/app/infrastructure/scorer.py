import math
from collections import Counter

from app.core.constants import CORE_ENGINES, SEVERITY_PENALTIES, EngineStatus, Severity
from app.domain.contracts.scorer import AbstractScorer, CapacityMetrics, Violation
from app.domain.entities.score import Score


class ProductionReadinessScorer(AbstractScorer):
    """Dynamically computes production readiness scores from violations
    and optional capacity / load-test data.

    * **Blocked state**: If a core engine (security, maintainability)
      is ``failed`` or ``not_configured``, the overall score is set to
      ``None`` and ``blocked_by`` lists the failing engine IDs.
    * **NULL initialisation**: Categories with zero violations AND no
      external data return ``None`` (rendered as N/A).
    * **Log-normalized per-rule scoring**: Violations are grouped by
      ``(category, rule_id, severity)``. Within each group, the base
      penalty is scaled by ``log(1 + count) / log(1 + total_files)``,
      so that the same rule firing 1 × on a 10 k-file project costs the
      same as firing 1 × on a 100-file project. This prevents finding
      counts from dominating scores on large projects.
    * **Capacity penalties**: Simulation results apply major penalties
      to performance when the system is explicitly failing or degraded.
    * **Critical-Floor formula**: The overall is the simple arithmetic
      mean of all active category scores; if any category drops below
      50 the overall is capped at that category's value.
    """

    CATEGORY_ORDER = [
        "performance",
        "security",
        "reliability",
        "maintainability",
        "devops",
    ]

    SIMULATION_FAILING_PENALTY = 50.0
    SIMULATION_DEGRADED_PENALTY = 20.0
    CRITICAL_FLOOR_THRESHOLD = 50.0

    BLOCKING_STATUSES: set[str] = {
        EngineStatus.FAILED,
        EngineStatus.NOT_CONFIGURED,
    }

    def calculate(
        self,
        violations: list[Violation],
        capacity: CapacityMetrics | None = None,
        engine_statuses: dict[str, str] | None = None,
        total_files: int = 0,
    ) -> Score:
        engine_statuses = engine_statuses or {}
        n_files = max(1, total_files)
        log_n_files = math.log(1 + n_files)

        # ── 0. Check for blocking engine failures ──────────────────────
        blocked_by: list[str] = []
        for engine_id in CORE_ENGINES:
            status = engine_statuses.get(engine_id)
            if status in self.BLOCKING_STATUSES:
                blocked_by.append(f"{engine_id}:{status}")

        # ── 1. External capacity data ──────────────────────────────────
        has_data: set[str] = set()
        category_scores: dict[str, float] = {}
        severity_counts: dict[str, int] = {s.value: 0 for s in Severity}

        if capacity is not None and capacity.has_data:
            has_data.add("performance")
            category_scores["performance"] = 100.0

        # ── 2. Log-normalized per-rule scoring ─────────────────────────
        # Group violations by (category, rule_id, severity) and apply
        #   penalty = base × log(1 + count) / log(1 + total_files)
        # so that a rule that fires many times on a large project does
        # not dominate the score.
        rule_groups: Counter[tuple[str, str, str]] = Counter()
        for v in violations:
            cat = v.category.lower()
            sev = v.severity.lower()
            if sev in severity_counts:
                severity_counts[sev] += 1
            if cat in self.CATEGORY_ORDER:
                has_data.add(cat)
                rule_groups[(cat, v.rule_id, sev)] += 1

        for cat in has_data:
            if cat not in category_scores:
                category_scores[cat] = 100.0

        for (cat, _rule_id, sev), count in rule_groups.items():
            try:
                sev_enum = Severity(sev)
                base_penalty = SEVERITY_PENALTIES.get(sev_enum, 0)
            except ValueError:
                base_penalty = 0
            if base_penalty == 0:
                continue
            normalized_factor = math.log(1 + count) / log_n_files
            category_scores[cat] -= base_penalty * normalized_factor

        # ── 3. Capacity-based performance penalties ─────────────────────
        if capacity is not None and capacity.has_data and "performance" in has_data:
            if capacity.simulation_status == "failing":
                category_scores["performance"] -= self.SIMULATION_FAILING_PENALTY
            elif capacity.simulation_status == "degraded":
                category_scores["performance"] -= self.SIMULATION_DEGRADED_PENALTY

        # ── 4. Clamp to [0, 100] ───────────────────────────────────────
        for cat in category_scores:
            category_scores[cat] = max(0.0, min(100.0, category_scores[cat]))

        # ── 5. Overall computation with Critical-Floor or Blocked ───────
        active = [c for c in self.CATEGORY_ORDER if c in has_data]
        if blocked_by:
            overall: int | None = None
        elif active:
            raw_overall = sum(category_scores[c] for c in active) / len(active)
            min_active = min(category_scores[c] for c in active)
            if min_active < self.CRITICAL_FLOOR_THRESHOLD:
                overall = round(min(raw_overall, min_active))
            else:
                overall = round(raw_overall)
            overall = max(0, min(100, overall))
        else:
            overall = None
            blocked_by = ["no_data:no_active_engines"]

        display_statuses = {
            e: engine_statuses.get(e, EngineStatus.NOT_CONFIGURED)
            for e in self.CATEGORY_ORDER
        }

        return Score(
            overall=overall,
            performance=(
                max(0, min(100, round(category_scores["performance"])))
                if "performance" in has_data
                else None
            ),
            security=(
                max(0, min(100, round(category_scores["security"])))
                if "security" in has_data
                else None
            ),
            reliability=(
                max(0, min(100, round(category_scores["reliability"])))
                if "reliability" in has_data
                else None
            ),
            maintainability=(
                max(0, min(100, round(category_scores["maintainability"])))
                if "maintainability" in has_data
                else None
            ),
            devops=(
                max(0, min(100, round(category_scores["devops"])))
                if "devops" in has_data
                else None
            ),
            blocked_by=blocked_by,
            engine_statuses=display_statuses,
            findings_count=sum(severity_counts.values()),
            critical_count=severity_counts.get(Severity.CRITICAL.value, 0),
            high_count=severity_counts.get(Severity.HIGH.value, 0),
            medium_count=severity_counts.get(Severity.MEDIUM.value, 0),
            low_count=severity_counts.get(Severity.LOW.value, 0),
        )
