
from app.core.constants import Category, Severity
from app.domain.entities.score import Score
from app.domain.rules.base import RuleViolation
from app.workers.dead_code.detector import DeadCodeFinding
from app.workers.enterprise_guide import EnterpriseGuide, EnterpriseGuideGenerator
from app.workers.errors.scanner import ErrorFinding
from app.workers.perf.load_sim import SimulationResult
from app.workers.perf.rpm_calculator import PerformanceMetrics


def _make_violation(
    rule_id: str = "TEST-001",
    severity: Severity = Severity.HIGH,
    category: Category = Category.SECURITY,
    title: str = "Test finding",
    file_path: str = "app.py",
    line_start: int = 1,
    description: str = "A test finding",
    recommendation: str = "Fix it",
    rpm_impact: int = 100,
    score_impact: float = 8.0,
) -> RuleViolation:
    return RuleViolation(
        rule_id=rule_id,
        severity=severity,
        category=category,
        title=title,
        file_path=file_path,
        line_start=line_start,
        description=description,
        recommendation=recommendation,
        rpm_impact=rpm_impact,
        score_impact=score_impact,
    )


class TestEnterpriseGuideGenerator:
    async def test_executive_summary_generated(self) -> None:
        score = Score(overall=85, security=90, performance=80, reliability=85, maintainability=80, devops=90)
        findings = [_make_violation()]
        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(findings=findings, scores=score)
        assert guide.executive_summary
        assert "85/100" in guide.executive_summary

    async def test_findings_grouped_by_severity(self) -> None:
        findings = [
            _make_violation(severity=Severity.CRITICAL, title="Critical issue"),
            _make_violation(severity=Severity.HIGH, title="High issue"),
            _make_violation(severity=Severity.MEDIUM, title="Medium issue"),
        ]
        score = Score(overall=70)
        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(findings=findings, scores=score)
        assert len(guide.critical_issues) == 1
        assert len(guide.high_issues) == 1
        assert len(guide.medium_issues) >= 1

    async def test_architecture_review_generated(self) -> None:
        findings = [
            _make_violation(category=Category.SECURITY),
            _make_violation(category=Category.PERFORMANCE, rule_id="PERF-001"),
        ]
        score = Score(overall=85)
        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(findings=findings, scores=score)
        assert guide.architecture_review is not None
        assert guide.architecture_review["total_findings"] == 2

    async def test_capacity_analysis_with_metrics(self) -> None:
        perf_metrics = PerformanceMetrics(
            overall_rpm=1500, breaks_at_concurrent_users=5000,
            bottlenecks=["n_plus_one"],
        )
        score = Score(overall=85)
        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(
            findings=[], scores=score, perf_metrics=perf_metrics,
        )
        assert guide.capacity_analysis is not None
        assert guide.capacity_analysis["estimated_rpm"] == 1500

    async def test_capacity_analysis_without_metrics(self) -> None:
        score = Score(overall=85)
        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(findings=[], scores=score)
        assert guide.capacity_analysis is not None
        assert guide.capacity_analysis.get("status") == "not_available"

    async def test_migration_path_sorted_by_priority(self) -> None:
        findings = [
            _make_violation(severity=Severity.CRITICAL, title="Critical fix", rpm_impact=500, score_impact=15.0),
            _make_violation(severity=Severity.HIGH, title="High fix", rpm_impact=50, score_impact=8.0),
        ]
        score = Score(overall=60)
        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(findings=findings, scores=score)
        assert len(guide.migration_path) == 2
        assert guide.migration_path[0]["step"] < guide.migration_path[1]["step"]  # type: ignore[operator]

    async def test_dead_code_included_in_issues(self) -> None:
        dead_code = [
            DeadCodeFinding(
                code_type="unused_import",
                name="os",
                file_path="app.py",
                line_start=1,
                evidence="Import 'os' is never used",
                confidence=0.95,
            ),
        ]
        score = Score(overall=85)
        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(
            findings=[], scores=score, dead_code=dead_code,
        )
        total_issues = len(guide.medium_issues)
        assert total_issues >= 1

    async def test_errors_included_in_issues(self) -> None:
        errors = [
            ErrorFinding(
                error_type="bare_except",
                severity="high",
                title="Bare except clause",
                description="Catches all exceptions",
                file_path="app.py",
                line_start=10,
            ),
        ]
        score = Score(overall=85)
        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(
            findings=[], scores=score, errors=errors,
        )
        high_count = len(guide.high_issues)
        assert high_count >= 1

    async def test_simulation_results_in_summary(self) -> None:
        score = Score(overall=85)
        sim_results = [
            SimulationResult(
                concurrent_users=5000, status="degraded",
                overall_rpm=800, error_rate_pct=5.0,
            ),
        ]
        generator = EnterpriseGuideGenerator()
        guide = await generator.generate(
            findings=[], scores=score, simulation=sim_results,
        )
        assert "5000" in guide.executive_summary

    async def test_to_dict_serialization(self) -> None:
        guide = EnterpriseGuide()
        guide.executive_summary = "Test summary"
        d = guide.to_dict()
        assert d["executive_summary"] == "Test summary"
        assert "critical_issues" in d
        assert "migration_path" in d
