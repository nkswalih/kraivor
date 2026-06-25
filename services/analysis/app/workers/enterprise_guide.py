from app.core.constants import Severity, Tiers
from app.core.logging import get_logger
from app.domain.entities.score import Score
from app.domain.rules.base import RuleViolation
from app.workers.dead_code.detector import DeadCodeFinding
from app.workers.errors.scanner import ErrorFinding
from app.workers.perf.load_sim import SimulationResult
from app.workers.perf.rpm_calculator import PerformanceMetrics

logger = get_logger(__name__)


class EnterpriseGuide:
    def __init__(self) -> None:
        self.executive_summary: str = ""
        self.critical_issues: list[dict] = []
        self.high_issues: list[dict] = []
        self.medium_issues: list[dict] = []
        self.architecture_review: dict | None = None
        self.capacity_analysis: dict | None = None
        self.migration_path: list[dict] = []

    def to_dict(self) -> dict:
        return {
            "executive_summary": self.executive_summary,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "medium_issues": self.medium_issues,
            "architecture_review": self.architecture_review,
            "capacity_analysis": self.capacity_analysis,
            "migration_path": self.migration_path,
        }


class EnterpriseGuideGenerator:
    async def generate(
        self,
        findings: list[RuleViolation],
        scores: Score,
        perf_metrics: PerformanceMetrics | None = None,
        simulation: list[SimulationResult] | None = None,
        dead_code: list[DeadCodeFinding] | None = None,
        errors: list[ErrorFinding] | None = None,
    ) -> EnterpriseGuide:
        guide = EnterpriseGuide()
        self._generate_executive_summary(guide, scores, perf_metrics, simulation)
        self._group_findings_by_severity(guide, findings, dead_code, errors)
        self._generate_architecture_review(guide, findings)
        self._generate_capacity_analysis(guide, perf_metrics, simulation)
        self._generate_migration_path(guide, findings, perf_metrics)
        return guide

    def _generate_executive_summary(
        self,
        guide: EnterpriseGuide,
        scores: Score,
        perf_metrics: PerformanceMetrics | None,
        simulation: list[SimulationResult] | None,
    ) -> None:
        tier_label = scores.tier.value if isinstance(scores.tier, Tiers) else str(scores.tier)
        parts = [
            f"Production Readiness Score: {scores.overall}/100 ({tier_label})",
            f"Security: {scores.security} | Performance: {scores.performance} | "
            f"Reliability: {scores.reliability} | Maintainability: {scores.maintainability} | "
            f"DevOps: {scores.devops}",
        ]
        if perf_metrics:
            parts.append(f"Estimated System RPM: {perf_metrics.overall_rpm}")
            parts.append(f"Breaks at: {perf_metrics.breaks_at_concurrent_users} concurrent users")
        if simulation and len(simulation) > 0:
            last = simulation[-1]
            parts.append(f"Simulation status at {last.concurrent_users} users: {last.status}")
        guide.executive_summary = "\n".join(parts)

    def _group_findings_by_severity(
        self,
        guide: EnterpriseGuide,
        findings: list[RuleViolation],
        dead_code: list[DeadCodeFinding] | None,
        errors: list[ErrorFinding] | None,
    ) -> None:
        all_entries: list[tuple[str, str, str, str, str, str, int]] = []
        for f in findings:
            entry = (
                f.title,
                f"{f.file_path}:{f.line_start}" if f.file_path else "unknown",
                str(f.severity),
                (f.description or "")[:200],
                f.recommendation or "",
                getattr(f, "enterprise_pattern", "") or "",
                self._estimate_fix_effort(f),
            )
            all_entries.append((f.severity, *entry))

        if dead_code:
            for dc in dead_code:
                all_entries.append((
                    Severity.MEDIUM,
                    f"Dead code: {dc.name}",
                    f"{dc.file_path}:{dc.line_start}" if dc.line_start else dc.file_path,
                    Severity.MEDIUM,
                    dc.evidence or dc.name,
                    "Remove unused code to improve maintainability",
                    f"Dead code pattern: {dc.code_type}",
                    0,
                ))

        if errors:
            for err in errors:
                all_entries.append((
                    err.severity,
                    err.title,
                    f"{err.file_path}:{err.line_start}" if err.line_start else err.file_path,
                    err.severity,
                    (err.description or "")[:200],
                    err.recommendation or "",
                    "",
                    self._estimate_fix_effort_from_title(err.title),
                ))

        for severity, title, file_ref, sev, desc, rec, ep, effort in all_entries:
            entry = {
                "title": title,
                "file": file_ref,
                "severity": sev,
                "impact": desc,
                "recommendation": rec,
                "enterprise_pattern": ep,
                "estimated_effort": effort,
            }
            if sev in ("critical", Severity.CRITICAL):
                guide.critical_issues.append(entry)
            elif sev in ("high", Severity.HIGH):
                guide.high_issues.append(entry)
            elif sev in ("medium", Severity.MEDIUM):
                guide.medium_issues.append(entry)

    def _generate_architecture_review(
        self, guide: EnterpriseGuide, findings: list[RuleViolation],
    ) -> None:
        total = len(findings)
        by_category: dict[str, int] = {}
        for f in findings:
            cat = str(f.category)
            by_category[cat] = by_category.get(cat, 0) + 1
        most_affected = sorted(by_category.items(), key=lambda x: -x[1])[:3]
        guide.architecture_review = {
            "total_findings": total,
            "most_affected_areas": [
                {"category": cat, "count": count} for cat, count in most_affected
            ],
            "summary": f"Found {total} issues across {len(by_category)} categories. "
            f"Primary concerns: {', '.join(c for c, _ in most_affected)}."
            if most_affected else "No significant architectural concerns detected.",
        }

    def _generate_capacity_analysis(
        self,
        guide: EnterpriseGuide,
        perf_metrics: PerformanceMetrics | None,
        simulation: list[SimulationResult] | None,
    ) -> None:
        if not perf_metrics:
            guide.capacity_analysis = {"status": "not_available"}
            return
        capacity: dict = {
            "estimated_rpm": perf_metrics.overall_rpm,
            "breaks_at_concurrent_users": perf_metrics.breaks_at_concurrent_users,
            "bottlenecks": perf_metrics.bottlenecks,
        }
        if simulation:
            capacity["simulation_results"] = [
                {
                    "users": s.concurrent_users,
                    "status": s.status,
                    "error_rate_pct": s.error_rate_pct,
                    "overall_rpm": s.overall_rpm,
                }
                for s in simulation
            ]
        guide.capacity_analysis = capacity

    def _generate_migration_path(
        self,
        guide: EnterpriseGuide,
        findings: list[RuleViolation],
        perf_metrics: PerformanceMetrics | None,
    ) -> None:
        steps: list[dict] = []
        for f in findings:
            if str(f.severity) not in ("critical", "high"):
                continue
            effort = self._estimate_fix_effort(f)
            rpm_gain = abs(f.rpm_impact) if f.rpm_impact else 50
            score_gain = abs(f.score_impact)
            priority_score = (rpm_gain + score_gain * 10) / max(effort, 1)
            steps.append({
                "action": f.title,
                "file": f"{f.file_path}:{f.line_start}" if f.file_path else "unknown",
                "effort_minutes": effort,
                "rpm_impact": f"+{rpm_gain} RPM",
                "score_impact": f"+{score_gain} points",
                "fix_snippet": f.recommendation,
                "priority_score": priority_score,
            })
        steps.sort(key=lambda s: s["priority_score"], reverse=True)
        for i, step in enumerate(steps, 1):
            step["step"] = i
            del step["priority_score"]
        guide.migration_path = steps

    def _estimate_fix_effort(self, finding: RuleViolation) -> int:
        effort_map = {
            "unused_import": 2,
            "missing_timeout": 5,
            "bare_except": 5,
            "n_plus_one": 15,
            "missing_auth": 20,
            "hardcoded_secret": 10,
            "swallowed_exception": 10,
            "sync_in_async": 30,
            "high_complexity": 45,
        }
        for pattern, effort in effort_map.items():
            if pattern in finding.title.lower() or pattern in finding.rule_id.lower():
                return effort
        return 30

    def _estimate_fix_effort_from_title(self, title: str) -> int:
        effort_map = {
            "bare except": 5,
            "swallowed": 10,
            "timeout": 5,
            "logged": 10,
            "unused": 2,
        }
        title_lower = title.lower()
        for pattern, effort in effort_map.items():
            if pattern in title_lower:
                return effort
        return 15
