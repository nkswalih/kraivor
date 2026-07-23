"""Tests for handler-level functions — dedup, save_findings, stage_score."""

from typing import cast

from app.application.analysis.handler import _dedup_violations
from app.core.constants import Category, Severity
from app.domain.rules.base import RuleViolation

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
