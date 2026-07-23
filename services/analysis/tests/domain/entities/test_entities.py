from uuid import UUID, uuid4

from app.core.constants import Category, Severity, Tiers
from app.domain.entities.finding import Finding
from app.domain.entities.report import Report
from app.domain.entities.repository import Repository
from app.domain.entities.score import Score


class TestFinding:
    def test_create_finding(self) -> None:
        finding = Finding(
            job_id=uuid4(),
            repo_id=uuid4(),
            workspace_id=uuid4(),
            rule_id="QUAL-COMPLEX",
            category=Category.MAINTAINABILITY,
            severity=Severity.MEDIUM,
            title="High complexity",
            file_path="src/main.py",
            line_start=10,
            line_end=25,
        )
        assert isinstance(finding.id, UUID)
        assert finding.rule_id == "QUAL-COMPLEX"
        assert finding.category == Category.MAINTAINABILITY

    def test_finding_with_optional_fields(self) -> None:
        finding = Finding(
            job_id=uuid4(),
            repo_id=uuid4(),
            workspace_id=uuid4(),
            rule_id="SEC-NO-AUTH",
            category=Category.SECURITY,
            severity=Severity.CRITICAL,
            title="Missing auth",
            file_path="routes.py",
            line_start=5,
            line_end=5,
            description="No auth on this route",
            recommendation="Add JWT auth",
            score_impact=-15.0,
        )
        assert finding.score_impact == -15.0
        assert finding.recommendation == "Add JWT auth"

    def test_to_dict(self) -> None:
        finding = Finding(
            job_id=uuid4(),
            repo_id=uuid4(),
            workspace_id=uuid4(),
            rule_id="TEST",
            category=Category.QUALITY,
            severity=Severity.LOW,
            title="Test",
            file_path="test.py",
            line_start=1,
            line_end=1,
        )
        d = finding.to_dict()
        assert d["rule_id"] == "TEST"
        assert d["severity"] == "low"


class TestReport:
    def test_create_report(self) -> None:
        report = Report(
            job_id=uuid4(),
            repo_id=uuid4(),
            workspace_id=uuid4(),
            branch="main",
            total_files_analyzed=10,
        )
        assert report.total_files_analyzed == 10
        assert report.branch == "main"

    def test_report_with_scores(self) -> None:
        score = Score(overall=85)
        report = Report(
            job_id=uuid4(), repo_id=uuid4(), workspace_id=uuid4(), scores=score
        )
        assert report.scores is not None
        assert report.scores.overall == 85

    def test_to_dict(self) -> None:
        report = Report(job_id=uuid4(), repo_id=uuid4(), workspace_id=uuid4())
        d = report.to_dict()
        assert "metadata" in d
        assert "findings" in d


class TestRepository:
    def test_create_repository(self) -> None:
        repo = Repository(
            id=uuid4(),
            workspace_id=uuid4(),
            clone_url="https://github.com/user/repo.git",
            branch="main",
        )
        assert repo.clone_url == "https://github.com/user/repo.git"
        assert repo.branch == "main"


class TestScore:
    def test_create_score(self) -> None:
        score = Score(overall=85, performance=80, security=90)
        assert score.overall == 85
        assert score.performance == 80
        assert score.security == 90

    def test_score_tier_production_ready(self) -> None:
        score = Score(overall=95)
        assert score.tier == Tiers.PRODUCTION_READY

    def test_score_tier_minor_issues(self) -> None:
        score = Score(overall=80)
        assert score.tier == Tiers.MINOR_ISSUES

    def test_score_tier_critical(self) -> None:
        score = Score(overall=30)
        assert score.tier == Tiers.CRITICAL_STATE

    def test_default_dimensions(self) -> None:
        score = Score(overall=75)
        assert score.performance is None
        assert score.security is None
        assert score.reliability is None
        assert score.maintainability is None
        assert score.devops is None

    def test_to_dict(self) -> None:
        score = Score(overall=88, performance=85, security=90)
        d = score.to_dict()
        assert d["overall"] == 88
        assert d["performance"] == 85
        assert d["security"] == 90
        assert "tier" in d
