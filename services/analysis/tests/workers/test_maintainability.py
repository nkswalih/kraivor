"""Tests for the MaintainabilityDetector."""

import pytest

from app.domain.contracts.parser import ParsedClass, ParsedFile, ParsedFunction
from app.workers.maintainability.detector import MaintainabilityDetector
from app.workers.maintainability.models import MaintainabilityMetrics


def _make_pf(
    path: str,
    content: str,
    functions: list[ParsedFunction] | None = None,
    classes: list[ParsedClass] | None = None,
) -> ParsedFile:
    return ParsedFile(
        path=path,
        content=content,
        language="python",
        ast_data={},
        functions=functions or [],
        classes=classes or [],
        imports=[],
        exports=[],
        routes=[],
        lines_count=len(content.split("\n")),
        errors=[],
        size_bytes=len(content.encode("utf-8")),
    )


@pytest.mark.asyncio
class TestLongMethod:
    async def test_detects_long_method(self) -> None:
        lines = "\n".join(f"print({i})" for i in range(55))
        content = f"def long_func():\n{lines}\n"
        pf = _make_pf("long.py", content, functions=[
            ParsedFunction(name="long_func", line_start=1, line_end=57, complexity=1),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "long_method" in types

    async def test_skips_short_method(self) -> None:
        lines = "\n".join(f"print({i})" for i in range(10))
        content = f"def short_func():\n{lines}\n"
        pf = _make_pf("short.py", content, functions=[
            ParsedFunction(name="short_func", line_start=1, line_end=12, complexity=1),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "long_method" not in types


@pytest.mark.asyncio
class TestTooManyParameters:
    async def test_detects_too_many_parameters(self) -> None:
        content = "def overloaded(a, b, c, d, e, f, g):\n    pass\n"
        pf = _make_pf("params.py", content, functions=[
            ParsedFunction(name="overloaded", line_start=1, line_end=2, complexity=1),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "too_many_parameters" in types

    async def test_skips_few_parameters(self) -> None:
        content = "def simple(a, b, c):\n    pass\n"
        pf = _make_pf("params.py", content, functions=[
            ParsedFunction(name="simple", line_start=1, line_end=2, complexity=1),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "too_many_parameters" not in types


@pytest.mark.asyncio
class TestHighCyclomaticComplexity:
    async def test_detects_high_complexity(self) -> None:
        pf = _make_pf("complex.py", "def complex_func():\n    pass\n", functions=[
            ParsedFunction(name="complex_func", line_start=1, line_end=2, complexity=15),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "high_cyclomatic_complexity" in types

    async def test_skips_low_complexity(self) -> None:
        pf = _make_pf("simple.py", "def simple():\n    pass\n", functions=[
            ParsedFunction(name="simple", line_start=1, line_end=2, complexity=3),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "high_cyclomatic_complexity" not in types


@pytest.mark.asyncio
class TestDeepNesting:
    async def test_detects_deep_nesting(self) -> None:
        content = (
            "if a:\n"
            "    if b:\n"
            "        if c:\n"
            "            if d:\n"
            "                if e:\n"
            "                    if f:\n"
            "                        print('deep')\n"
        )
        pf = _make_pf("nest.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "deep_nesting" in types

    async def test_skips_shallow_nesting(self) -> None:
        content = (
            "if a:\n"
            "    if b:\n"
            "        if c:\n"
            "            print('ok')\n"
        )
        pf = _make_pf("nest.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "deep_nesting" not in types


@pytest.mark.asyncio
class TestDuplicateCode:
    async def test_detects_duplicate_code(self) -> None:
        content = (
            "save_record(record)\n"
            "update_cache(record)\n"
            "log_action(record)\n"
            "x = 1\n"
            "save_record(record)\n"
            "update_cache(record)\n"
            "log_action(record)\n"
        )
        pf = _make_pf("dup.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "duplicate_code" in types

    async def test_skips_no_duplicates(self) -> None:
        content = (
            "save_record(record)\n"
            "update_cache(record)\n"
            "log_action(record)\n"
        )
        pf = _make_pf("dup.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "duplicate_code" not in types


@pytest.mark.asyncio
class TestLargeClass:
    async def test_detects_large_class(self) -> None:
        pf = _make_pf("large.py", "class Large:\n    pass\n", classes=[
            ParsedClass(name="Large", line_start=1, line_end=350, methods=["a"]),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "large_class" in types

    async def test_skips_small_class(self) -> None:
        pf = _make_pf("small.py", "class Small:\n    pass\n", classes=[
            ParsedClass(name="Small", line_start=1, line_end=50, methods=["a"]),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "large_class" not in types


@pytest.mark.asyncio
class TestTooManyMethods:
    async def test_detects_too_many_methods(self) -> None:
        pf = _make_pf("big.py", "class Big:\n    pass\n", classes=[
            ParsedClass(name="Big", line_start=1, line_end=100, methods=[f"m{i}" for i in range(20)]),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "too_many_methods" in types

    async def test_skips_reasonable_methods(self) -> None:
        pf = _make_pf("ok.py", "class Ok:\n    pass\n", classes=[
            ParsedClass(name="Ok", line_start=1, line_end=50, methods=[f"m{i}" for i in range(5)]),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "too_many_methods" not in types


@pytest.mark.asyncio
class TestLongLine:
    async def test_detects_long_line(self) -> None:
        content = "x = " + "a" * 200 + "\n"
        pf = _make_pf("longline.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "long_line" in types

    async def test_skips_short_lines(self) -> None:
        content = "x = 1\n"
        pf = _make_pf("short.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "long_line" not in types


@pytest.mark.asyncio
class TestMissingDocstrings:
    async def test_detects_missing_docstring_on_function(self) -> None:
        pf = _make_pf("mod.py", "def public_func():\n    pass\n", functions=[
            ParsedFunction(name="public_func", line_start=1, line_end=2, complexity=1, docstring=""),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "missing_docstring" in types

    async def test_skips_function_with_docstring(self) -> None:
        pf = _make_pf("mod.py", "def doc_func():\n    '''Has docs.'''\n    pass\n", functions=[
            ParsedFunction(name="doc_func", line_start=1, line_end=3, complexity=1, docstring="Has docs."),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "missing_docstring" not in types

    async def test_skips_private_function(self) -> None:
        pf = _make_pf("mod.py", "def _helper():\n    pass\n", functions=[
            ParsedFunction(name="_helper", line_start=1, line_end=2, complexity=1, docstring=""),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "missing_docstring" not in types


@pytest.mark.asyncio
class TestMagicNumbers:
    async def test_detects_magic_number(self) -> None:
        content = (
            "def calc():\n"
            "    return 42\n"
        )
        pf = _make_pf("magic.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "magic_number" in types

    async def test_skips_common_values(self) -> None:
        content = (
            "for i in range(10):\n"
            "    print(i)\n"
        )
        pf = _make_pf("range.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "magic_number" not in types


@pytest.mark.asyncio
class TestEmptyCatchBlocks:
    async def test_detects_empty_except(self) -> None:
        content = (
            "try:\n"
            "    risky()\n"
            "except:\n"
            "    pass\n"
        )
        pf = _make_pf("except.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "empty_catch_block" in types

    async def test_skips_except_with_handling(self) -> None:
        content = (
            "try:\n"
            "    risky()\n"
            "except Exception as e:\n"
            "    logger.exception('error')\n"
        )
        pf = _make_pf("except.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "empty_catch_block" not in types


@pytest.mark.asyncio
class TestTodoComments:
    async def test_detects_todo_comment(self) -> None:
        content = "# TODO: implement this later\n"
        pf = _make_pf("todo.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "todo_comment" in types

    async def test_detects_fixme_comment(self) -> None:
        content = "# FIXME: this is broken\n"
        pf = _make_pf("fixme.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "todo_comment" in types

    async def test_skips_normal_comments(self) -> None:
        content = "# This is a normal comment\n"
        pf = _make_pf("normal.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "todo_comment" not in types


@pytest.mark.asyncio
class TestDeepInheritance:
    async def test_detects_deep_inheritance(self) -> None:
        pf = _make_pf("inherits.py", "class A(B, C, D, E):\n    pass\n", classes=[
            ParsedClass(name="A", line_start=1, line_end=2, bases=["B", "C", "D", "E"], methods=["method"]),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "deep_inheritance" in types

    async def test_skips_shallow_inheritance(self) -> None:
        pf = _make_pf("inherits.py", "class A(Base):\n    pass\n", classes=[
            ParsedClass(name="A", line_start=1, line_end=2, bases=["Base"], methods=["method"]),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "deep_inheritance" not in types


@pytest.mark.asyncio
class TestCircularImports:
    async def test_detects_import_inside_function(self) -> None:
        content = (
            "def handler():\n"
            "    from app.models import User\n"
            "    return User()\n"
        )
        pf = _make_pf("circular.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "circular_import" in types

    async def test_skips_imports_at_top(self) -> None:
        content = (
            "from app.models import User\n"
            "def handler():\n"
            "    return User()\n"
        )
        pf = _make_pf("top.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "circular_import" not in types

    async def test_skips_typing_import_inside_function(self) -> None:
        content = (
            "def handler():\n"
            "    from typing import List\n"
            "    return []\n"
        )
        pf = _make_pf("typing.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        types = [r.maintainability_type for r in results]
        assert "circular_import" not in types


@pytest.mark.asyncio
class TestEdgeCases:
    async def test_empty_content_no_findings(self) -> None:
        pf = _make_pf("empty.py", "")
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        assert len(results) == 0

    async def test_binary_content_no_crash(self) -> None:
        pf = _make_pf("binary.bin", "\x00\x01\x02\x03\xff\xfe\xfd\xfc")
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        assert isinstance(results, list)

    async def test_very_large_content_no_crash(self) -> None:
        content = "x = 1\n" * 10000
        pf = _make_pf("large.py", content)
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        assert isinstance(results, list)

    async def test_no_files_no_findings(self) -> None:
        detector = MaintainabilityDetector([])
        results = await detector.scan_all()
        assert len(results) == 0


@pytest.mark.asyncio
class TestMetricsComputation:
    async def test_empty_metrics(self) -> None:
        detector = MaintainabilityDetector([])
        metrics = detector.compute_metrics([])
        assert metrics.maintainability_index == 100.0
        assert metrics.technical_debt_hours == 0.0
        assert metrics.complexity_score == 100.0
        assert metrics.total_findings == 0

    async def test_metrics_with_findings(self) -> None:
        pf = _make_pf("test.py", "def f():\n    pass\n", functions=[
            ParsedFunction(name="f", line_start=1, line_end=60, complexity=15),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        metrics = detector.compute_metrics(results)
        assert metrics.total_findings > 0
        assert metrics.maintainability_index < 100.0
        assert metrics.technical_debt_hours > 0.0
        assert metrics.complexity_score < 100.0

    async def test_metrics_maintainability_index_formula(self) -> None:
        pf = _make_pf("test.py", "def f():\n    pass\n", functions=[
            ParsedFunction(name="f", line_start=1, line_end=60, complexity=12),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        metrics = detector.compute_metrics(results)
        assert isinstance(metrics.maintainability_index, float)
        assert 0 <= metrics.maintainability_index <= 100

    async def test_metrics_exact_values(self) -> None:
        pf = _make_pf("test.py", "x = 1\n", functions=[
            ParsedFunction(name="f", line_start=1, line_end=2, complexity=1),
        ])
        detector = MaintainabilityDetector([pf])
        results = await detector.scan_all()
        metrics = detector.compute_metrics(results)
        long_methods = sum(1 for f in results if f.maintainability_type == "long_method")
        assert long_methods == 0
        assert metrics.maintainability_index >= 90

    async def test_metrics_dict_conversion(self) -> None:
        metrics = MaintainabilityMetrics(
            maintainability_index=75.5,
            technical_debt_hours=12.0,
            complexity_score=60.0,
            total_findings=10,
        )
        d = metrics.to_dict()
        assert d["maintainability_index"] == 75.5
        assert d["technical_debt_hours"] == 12.0
        assert d["complexity_score"] == 60.0
        assert d["total_findings"] == 10

    async def test_finding_to_dict(self) -> None:
        from app.workers.maintainability.models import MaintainabilityFinding
        finding = MaintainabilityFinding(
            maintainability_type="long_method",
            severity="medium",
            title="Test",
            description="Desc",
            file_path="f.py",
            line_start=1,
            line_end=10,
            code_snippet="code",
            recommendation="fix it",
            confidence=0.9,
            estimated_effort_hours=2.0,
        )
        d = finding.to_dict()
        assert d["maintainability_type"] == "long_method"
        assert d["estimated_effort_hours"] == 2.0
