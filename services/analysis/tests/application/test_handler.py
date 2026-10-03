"""Tests for handler-level functions - dedup, save_findings, stage_score."""

import asyncio
from typing import cast
from uuid import UUID, uuid4

import pytest

from app.application.analysis.handler import _dedup_violations, get_job_statistics
from app.application.analysis.queries import GetJobStatisticsQuery
from app.core.constants import Category, Severity
from app.domain.rules.base import RuleViolation
from app.infrastructure.db.unit_of_work import UnitOfWork

# ======================================================================
# _dedup_violations
# ======================================================================


def _rv(
    rule_id: str,
    file_path: str = "",
    line_start: int = 1,
    line_end: int = 1,
    **kw: object,
) -> RuleViolation:
    return RuleViolation(
        rule_id=rule_id,
        category=cast(Category, str(kw.get("category", "security"))),
        severity=cast(Severity, str(kw.get("severity", "critical"))),
        title=str(kw.get("title", "Test")),
        description=str(kw.get("description", "")),
        file_path=file_path,
        line_start=line_start,
        line_end=line_end,
    )


class TestDedupViolations:
    def test_empty_list(self) -> None:
        assert _dedup_violations([]) == []

    def test_single_violation_returned(self) -> None:
        v = _rv("SEC-SECRET", "app.py", 10, 12)
        result = _dedup_violations([v])
        assert len(result) == 1
        assert result[0] is v

    def test_exact_duplicates_deduped(self) -> None:
        v1 = _rv("SEC-SECRET", "app.py", 10, 12)
        v2 = _rv("SEC-SECRET", "app.py", 10, 12)
        result = _dedup_violations([v1, v2])
        assert len(result) == 1
        assert result[0] is v1  # first wins

    def test_same_rule_same_file_different_line_not_deduped(self) -> None:
        v1 = _rv("SEC-SECRET", "app.py", 10, 12)
        v2 = _rv("SEC-SECRET", "app.py", 20, 22)
        result = _dedup_violations([v1, v2])
        assert len(result) == 2

    def test_same_rule_different_file_not_deduped(self) -> None:
        v1 = _rv("SEC-SECRET", "app.py", 10, 12)
        v2 = _rv("SEC-SECRET", "other.py", 10, 12)
        result = _dedup_violations([v1, v2])
        assert len(result) == 2

    def test_different_rule_same_location_not_deduped(self) -> None:
        v1 = _rv("SEC-SECRET", "app.py", 10, 12)
        v2 = _rv("SEC-NO-AUTH", "app.py", 10, 12)
        result = _dedup_violations([v1, v2])
        assert len(result) == 2

    def test_mixed_dup_and_unique(self) -> None:
        v1 = _rv("SEC-SECRET", "a.py", 1, 1)
        v2 = _rv("SEC-SECRET", "a.py", 1, 1)  # dup of v1
        v3 = _rv("SEC-SECRET", "b.py", 1, 1)
        v4 = _rv("QUAL-COMPLEX", "a.py", 1, 1)
        result = _dedup_violations([v1, v2, v3, v4])
        assert len(result) == 3
        assert result[0] is v1
        assert result[1] is v3
        assert result[2] is v4

    def test_none_file_path(self) -> None:
        v1 = _rv("SEC-SECRET", "", 1, 1)
        v2 = _rv("SEC-SECRET", "", 1, 1)
        result = _dedup_violations([v1, v2])
        assert len(result) == 1

    def test_none_line_start_end(self) -> None:
        v1 = _rv("SEC-SECRET", "x.py", 0, 0)
        v2 = _rv("SEC-SECRET", "x.py", 0, 0)
        result = _dedup_violations([v1, v2])
        assert len(result) == 1


# ======================================================================
# get_job_statistics
# ======================================================================


class _Gate:
    """Released only once every expected caller has arrived.

    Each repository call awaits this. The handler therefore only completes if
    the seven calls genuinely overlap; awaited one after another, the first
    would block forever and `asyncio.wait_for` would time out. That is what
    makes this a real check on the gather rather than a smoke test.
    """

    def __init__(self, expected: int) -> None:
        self.expected = expected
        self.arrived = 0
        self._open = asyncio.Event()

    async def wait(self) -> None:
        self.arrived += 1
        if self.arrived >= self.expected:
            self._open.set()
        await self._open.wait()


class _FakeSession:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


def _repo_factory(
    name: str,
    results: dict[str, object],
    calls: list[tuple[str, str, UUID]],
    gate: _Gate | None,
) -> type:
    """Build a stand-in for a repository class.

    The handler invokes these as `getattr(repo_cls(session), method)`, so
    `__getattr__` is what has to answer. Each method returns a distinct value,
    which is what lets the tests below tell the seven concurrent results
    apart - a mis-wired positional unpack would otherwise pass silently.
    """

    class _Repo:
        def __init__(self, session: object) -> None:
            self.session = session

        def __getattr__(self, method: str):
            async def _call(job_id: UUID) -> object:
                calls.append((name, method, job_id))
                if gate is not None:
                    await gate.wait()
                return results[method]

            return _call

    return _Repo


def _install(
    monkeypatch: pytest.MonkeyPatch,
    *,
    severity: dict[str, int] | None = None,
    category: dict[str, int] | None = None,
    dead_code: int = 11,
    errors: int = 22,
    perf: int = 33,
    simulations: int = 44,
    guide_exists: bool = True,
    gate: _Gate | None = None,
) -> list[tuple[str, str, UUID]]:
    """Patch the repositories and session factory the handler imports lazily."""
    calls: list[tuple[str, str, UUID]] = []
    specs = [
        (
            "app.infrastructure.db.repositories.finding.FindingRepository",
            "FindingRepository",
            {
                "count_by_severity": {} if severity is None else severity,
                "count_by_category": {} if category is None else category,
            },
        ),
        (
            "app.infrastructure.db.repositories.dead_code.DeadCodeRepository",
            "DeadCodeRepository",
            {"count_by_job": dead_code},
        ),
        (
            "app.infrastructure.db.repositories.error_finding.ErrorFindingRepository",
            "ErrorFindingRepository",
            {"count_by_job": errors},
        ),
        (
            (
                "app.infrastructure.db.repositories.performance_metric."
                "PerformanceMetricRepository"
            ),
            "PerformanceMetricRepository",
            {"count_by_job": perf},
        ),
        (
            (
                "app.infrastructure.db.repositories.simulation_result."
                "SimulationResultRepository"
            ),
            "SimulationResultRepository",
            {"count_by_job": simulations},
        ),
        (
            (
                "app.infrastructure.db.repositories.enterprise_guide."
                "EnterpriseGuideRepository"
            ),
            "EnterpriseGuideRepository",
            {"exists_by_job": guide_exists},
        ),
    ]
    for target, name, results in specs:
        monkeypatch.setattr(target, _repo_factory(name, results, calls, gate))
    monkeypatch.setattr(
        "app.infrastructure.db.session.async_session_factory", _FakeSession
    )
    return calls


async def _stats(job_id: UUID) -> dict[str, object]:
    return await get_job_statistics(
        GetJobStatisticsQuery(job_id=job_id), cast(UnitOfWork, None)
    )


class TestGetJobStatistics:
    async def test_each_count_lands_on_its_own_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The seven concurrent results are unpacked positionally.

        Every repository returns a distinct value here, so swapping two
        results - the realistic bug in this shape of code - fails rather than
        passing.
        """
        _install(
            monkeypatch, severity={"critical": 1, "high": 2}, category={"security": 7}
        )

        assert await _stats(uuid4()) == {
            "findings_count": 3,
            "dead_code_count": 11,
            "error_findings_count": 22,
            "performance_metrics_count": 33,
            "simulation_results_count": 44,
            "enterprise_guide_exists": True,
            "counts_by_severity": {"critical": 1, "high": 2},
            "counts_by_category": {"security": 7},
        }

    async def test_every_count_is_scoped_to_the_requested_job(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        job_id = uuid4()
        calls = _install(monkeypatch)

        await _stats(job_id)

        assert len(calls) == 7
        assert {c[2] for c in calls} == {job_id}
        assert sorted(c[0] for c in calls) == [
            "DeadCodeRepository",
            "EnterpriseGuideRepository",
            "ErrorFindingRepository",
            "FindingRepository",
            "FindingRepository",
            "PerformanceMetricRepository",
            "SimulationResultRepository",
        ]

    async def test_the_counts_are_gathered_concurrently(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Guards the concurrency the handler depends on."""
        gate = _Gate(expected=7)
        _install(monkeypatch, gate=gate)

        # Would raise TimeoutError if the calls were awaited sequentially.
        result = await asyncio.wait_for(_stats(uuid4()), timeout=5)

        assert gate.arrived == 7
        assert result["dead_code_count"] == 11

    async def test_findings_count_is_zero_without_severities(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Covers the empty branch of `sum(...) if severity_counts else 0`."""
        _install(monkeypatch, severity={}, category={})

        result = await _stats(uuid4())

        assert result["findings_count"] == 0
        assert result["counts_by_severity"] == {}
        assert result["counts_by_category"] == {}

    async def test_missing_enterprise_guide_is_reported_as_false(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _install(monkeypatch, guide_exists=False)

        assert (await _stats(uuid4()))["enterprise_guide_exists"] is False

    async def test_a_failing_count_propagates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A partial payload would otherwise look like real zeroes."""
        seen: list[str] = []
        _install(monkeypatch)

        async def _boom(job_id: UUID) -> int:
            seen.append("count_by_job")
            raise RuntimeError("db gone")

        monkeypatch.setattr(
            "app.infrastructure.db.repositories.dead_code.DeadCodeRepository",
            type(
                "_Dead",
                (),
                {
                    "__init__": lambda self, session: None,
                    "__getattr__": lambda self, method: _boom,
                },
            ),
        )

        with pytest.raises(RuntimeError, match="db gone"):
            await _stats(uuid4())

        assert seen == ["count_by_job"]
