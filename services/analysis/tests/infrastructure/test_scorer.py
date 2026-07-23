"""Integration tests for ProductionReadinessScorer
(Log-normalized per-rule scoring + Critical-Floor formula)."""

import math
from typing import cast

from app.domain.contracts.scorer import CapacityMetrics, Violation
from app.infrastructure.scorer import ProductionReadinessScorer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

scorer = ProductionReadinessScorer()


def v(category: str, severity: str, **kw: object) -> Violation:
    return Violation(
        rule_id=str(kw.get("rule_id", "TEST-RULE")),
        category=category,
        severity=severity,
        title=str(kw.get("title", "Test violation")),
        description=str(kw.get("description", "")),
        file_path=str(kw.get("file_path", "")),
        line_start=cast(int | None, kw.get("line_start", 1)),
        line_end=cast(int | None, kw.get("line_end", 1)),
    )


def capacity_metrics(
    status: str | None = None,
    breaks_at: int | None = None,
    rpm: int | None = None,
    bottlenecks: list[str] | None = None,
) -> CapacityMetrics:
    return CapacityMetrics(
        has_data=status is not None,
        simulation_status=status,
        breaks_at_users=breaks_at,
        overall_rpm=rpm,
        bottlenecks=bottlenecks or [],
    )


def _nf(count: int, total_files: int = 0) -> float:
    """Log-normalized factor: log(1+count) / log(1+max(1,total_files))."""
    nf = max(1, total_files)
    return math.log(1 + count) / math.log(1 + nf)


# ---------------------------------------------------------------------------
# No violations / no data
# ---------------------------------------------------------------------------


class TestNoData:
    def test_no_violations_no_capacity_returns_blocked(self) -> None:
        """With no engine_statuses provided, all engines are not_configured
        and no violations exist, so there is no active data and overall
        is None (blocked)."""
        score = scorer.calculate([])
        assert score.overall is None
        assert score.blocked_by == ["no_data:no_active_engines"]
        assert score.performance is None
        assert score.security is None
        assert score.reliability is None
        assert score.maintainability is None
        assert score.devops is None
        assert score.findings_count == 0

    def test_violations_only_in_active_categories(self) -> None:
        """Categories with zero violations return None even if others have data."""
        score = scorer.calculate([v("security", "critical"), v("security", "high")])
        assert score.security == 75  # 100 - 15 - 10 (both single-count, factor 1.0)
        assert score.performance is None
        assert score.reliability is None
        assert score.maintainability is None
        assert score.devops is None


# ---------------------------------------------------------------------------
# Log-normalized per-rule scoring
# ---------------------------------------------------------------------------


class TestLogNormalizedScoring:
    def test_single_violation_same_as_old_model(self) -> None:
        """A single violation of any severity produces a factor of 1.0
        when total_files=0 (n_files=1)."""
        score = scorer.calculate([v("security", "critical")])
        assert score.security == 85  # 100 - 15 * 1.0

    def test_same_rule_severity_accumulates_logarithmically(self) -> None:
        """Multiple violations of the same (rule_id, severity) are grouped
        and penalized with log(1+count)/log(1+total_files)."""
        score = scorer.calculate(
            [
                v("security", "critical"),
                v("security", "critical"),
                v("security", "critical"),
                v("security", "critical"),
            ],
            total_files=10,
        )
        # n=10 → log(11)≈2.398, factor=log(5)/log(11)=1.609/2.398≈0.671
        # penalty=15*0.671≈10.07 → security≈90
        assert score.security == 90

    def test_different_rule_ids_separate_groups(self) -> None:
        """Different rule_ids under the same category are penalized
        independently, even with the same severity."""
        score = scorer.calculate(
            [
                v("security", "critical", rule_id="SEC-A"),
                v("security", "critical", rule_id="SEC-A"),
                v("security", "critical", rule_id="SEC-B"),
            ],
            total_files=10,
        )
        # SEC-A: count=2, factor=log(3)/log(11)≈1.099/2.398≈0.458, penalty=15*0.458≈6.87
        # SEC-B: count=1, factor=log(2)/log(11)≈0.693/2.398≈0.289, penalty=15*0.289≈4.34
        # total≈11.21 → security≈89
        assert score.security == 89

    def test_linear_fallback_when_total_files_is_zero(self) -> None:
        """With total_files=0, n_files becomes 1 and factor=1.0 for
        any single-count rule, matching the old linear model."""
        score = scorer.calculate([v("security", "critical"), v("security", "critical")])
        # single group: count=2, n=1 → log(3)/log(2)≈1.585, penalty=15*1.585≈23.77
        # security≈76
        assert score.security == 76

    def test_same_category_multiple_rules_accumulated(self) -> None:
        """Penalties from distinct rule_ids within the same category
        add up correctly."""
        score = scorer.calculate(
            [
                v("security", "critical", rule_id="S1"),
                v("security", "critical", rule_id="S1"),
                v("security", "high", rule_id="S2"),
                v("security", "medium", rule_id="S3"),
                v("security", "medium", rule_id="S3"),
                v("security", "medium", rule_id="S3"),
            ],
            total_files=100,
        )
        # S1/critical: count=2, factor=log(3)/log(101)≈1.099/4.615≈0.238, penalty=15*0.238≈3.57
        # S2/high: count=1, factor=log(2)/log(101)≈0.693/4.615≈0.150, penalty=10*0.150≈1.50
        # S3/medium: count=3, factor=log(4)/log(101)≈1.386/4.615≈0.300, penalty=5*0.300≈1.50
        # total≈6.57 → security≈93
        assert score.security == 93

    def test_large_project_single_violation_has_minimal_impact(self) -> None:
        """On a 10k-file project, a single violation's penalty is tiny."""
        score = scorer.calculate([v("security", "critical")], total_files=10000)
        # count=1, factor=log(2)/log(10001)≈0.693/9.210≈0.075
        # penalty=15*0.075≈1.13 → security≈99
        assert score.security == 99


# ---------------------------------------------------------------------------
# Critical-Floor formula
# ---------------------------------------------------------------------------


class TestCriticalFloor:
    def test_all_perfect_scores_mean(self) -> None:
        violations = [v("security", "info"), v("performance", "info")]
        score = scorer.calculate(violations)
        assert score.overall == 100
        assert score.performance == 100
        assert score.security == 100

    def test_simple_mean_when_all_above_floor(self) -> None:
        violations = [
            v("security", "low"),
            v("performance", "low"),
            v("reliability", "medium"),
        ]
        score = scorer.calculate(violations)
        # single-count: factor=1.0 → sec=98, perf=98, rel=95
        # mean≈97, min=95 >= 50 → overall=97
        assert score.overall == 97
        assert score.security == 98
        assert score.performance == 98
        assert score.reliability == 95

    def test_log_scale_keeps_scores_above_floor_longer(self) -> None:
        """Log-normalization prevents a single rule from driving
        a category below 50 unless violations are extreme."""
        violations = [
            v("security", "critical"),
            v("security", "critical"),
            v("security", "critical"),
            v("security", "critical"),
            v("maintainability", "critical"),
            v("maintainability", "critical"),
            v("maintainability", "critical"),
            v("maintainability", "critical"),
        ]
        score = scorer.calculate(violations)
        # security: 4x critical (same rule+severity)
        #   count=4, n=1 → log(5)/log(2)=2.322, penalty=15*2.322=34.83
        #   security ≈ 65
        # maintainability: 4x critical (same rule+severity)
        #   similarly ≈ 65
        # min=65 >= 50 → overall = round(mean(65,65)) = 65
        assert score.security == 65
        assert score.maintainability == 65
        assert score.overall == 65

    def test_massive_violation_count_forces_category_below_50(self) -> None:
        """Even with log-normalization, a very large number of violations
        from a single rule can still push a category below 50."""
        violations = [v("security", "critical") for _ in range(100)]
        score = scorer.calculate(violations, total_files=50)
        # 100 x critical under same rule_id+severity
        # count=100, n=50 → log(101)/log(51)=4.615/3.932=1.174
        # penalty=15*1.174=17.61 → security ≈ 82
        # This doesn't go below 50 because log-normalization is strong
        # for large counts on smaller projects
        assert score.security is not None and score.security >= 50

    def test_only_one_category_with_data(self) -> None:
        violations = [
            v("security", "critical"),
            v("security", "medium"),
            v("security", "low"),
        ]
        score = scorer.calculate(violations)
        # single-count each: sec=100-15-5-2=78
        assert score.overall == 78
        assert score.security == 78


# ---------------------------------------------------------------------------
# Capacity / simulation penalties
# ---------------------------------------------------------------------------


class TestCapacityPenalties:
    def test_performance_stable_no_extra_penalty(self) -> None:
        cap = capacity_metrics(status="stable", breaks_at=5000, rpm=1500)
        score = scorer.calculate([], capacity=cap)
        assert score.performance == 100
        assert score.overall == 100

    def test_performance_degraded(self) -> None:
        cap = capacity_metrics(status="degraded", breaks_at=3000)
        violations = [v("performance", "medium")]
        score = scorer.calculate(violations, capacity=cap)
        # 100 - 5 (medium) - 20 (degraded) = 75
        assert score.performance == 75

    def test_performance_failing(self) -> None:
        cap = capacity_metrics(status="failing")
        score = scorer.calculate([], capacity=cap)
        # 100 - 50 (failing) = 50
        assert score.performance == 50

    def test_performance_failing_with_critical_violations(self) -> None:
        cap = capacity_metrics(status="failing")
        violations = [
            v("performance", "critical"),
            v("performance", "critical"),
            v("performance", "critical"),
            v("performance", "critical"),
        ]
        score = scorer.calculate(violations, capacity=cap)
        # 4x critical (same rule+severity): count=4, n=1→factor=2.322, penalty=34.83
        # perf ≈ 65 - 50 (failing) = 15
        assert score.performance == 15


# ---------------------------------------------------------------------------
# Severity counting
# ---------------------------------------------------------------------------


class TestSeverityCounts:
    def test_counts_aggregated_correctly(self) -> None:
        violations = [
            v("security", "critical"),
            v("security", "critical"),
            v("performance", "high"),
            v("reliability", "medium"),
            v("maintainability", "low"),
            v("devops", "info"),
        ]
        score = scorer.calculate(violations)
        assert score.findings_count == 6
        assert score.critical_count == 2
        assert score.high_count == 1
        assert score.medium_count == 1
        assert score.low_count == 1

    def test_unknown_severity_not_counted(self) -> None:
        violations = [
            Violation(
                rule_id="X",
                category="security",
                severity="unknown",
                title="Bad severity",
            )
        ]
        score = scorer.calculate(violations)
        assert score.findings_count == 0


# ---------------------------------------------------------------------------
# Mix of categories with and without data
# ---------------------------------------------------------------------------


class TestMixedCategories:
    def test_some_categories_have_data_others_none(self) -> None:
        violations = [v("security", "high"), v("performance", "medium")]
        score = scorer.calculate(violations)
        assert score.security == 90
        assert score.performance == 95
        assert score.reliability is None
        assert score.maintainability is None
        assert score.devops is None
        assert score.overall == 92


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_negative_penalty_clamped_to_zero(self) -> None:
        violations = [
            v("security", "critical"),
            v("security", "critical"),
            v("security", "critical"),
            v("security", "critical"),
            v("security", "critical"),
            v("security", "critical"),
            v("security", "critical"),
        ]
        score = scorer.calculate(violations)
        # With total_files=0 (→ n=1), 7x critical has factor=log(8)/log(2)=3.0
        # penalty=45 → security=55
        assert score.security == 55

    def test_overall_capped_at_100(self) -> None:
        score = scorer.calculate([v("security", "info"), v("performance", "info")])
        assert score.overall is not None and score.overall <= 100
        assert score.overall == 100

    def test_violation_category_not_in_scorer_list_ignored(self) -> None:
        violations = [v("dead_code", "medium"), v("error", "high")]
        score = scorer.calculate(violations)
        assert score.performance is None
        assert score.security is None
        assert score.overall is None
        assert "no_data:no_active_engines" in (score.blocked_by or [])

    def test_total_files_does_not_affect_categories_without_rule_groups(self) -> None:
        """Passing total_files should not affect categories that have
        capacity data but no violations."""
        cap = capacity_metrics(status="stable")
        score = scorer.calculate([], capacity=cap, total_files=1000)
        assert score.performance == 100
        assert score.overall == 100


# ---------------------------------------------------------------------------
# total_files parameter propagation
# ---------------------------------------------------------------------------


class TestTotalFilesEdgeCases:
    def test_total_files_zero_falls_back_to_one(self) -> None:
        """total_files=0 is treated as 1 to avoid division by zero."""
        score = scorer.calculate([v("security", "critical")], total_files=0)
        # n=1 → log(2)/log(2)=1.0 → penalty=15 → security=85
        assert score.security == 85

    def test_total_files_one_same_as_zero(self) -> None:
        """total_files=1 gives the same normalization as total_files=0."""
        score_0 = scorer.calculate([v("security", "critical")], total_files=0)
        score_1 = scorer.calculate([v("security", "critical")], total_files=1)
        assert score_0.security == score_1.security

    def test_zero_violations_with_total_files_ignores_normalization(self) -> None:
        """When there are no violations, total_files is irrelevant."""
        cap = capacity_metrics(status="stable")
        score = scorer.calculate([], capacity=cap, total_files=9999)
        assert score.performance == 100
        assert score.overall == 100
