import pytest

from app.domain.contracts.parser import ParsedFile, ParsedFunction, ParsedImport
from app.workers.dead_code.detector import DeadCodeDetector


def _make_pf(
    path: str,
    content: str = "",
    functions: list | None = None,
    imports: list | None = None,
    function_calls: list | None = None,
    exports: list | None = None,
    classes: list | None = None,
    routes: list | None = None,
) -> ParsedFile:
    return ParsedFile(
        path=path,
        language="python",
        content=content,
        size_bytes=len(content),
        lines_count=len(content.split("\n")),
        functions=functions or [],
        imports=imports or [],
        function_calls=function_calls or [],
        exports=exports or [],
        classes=classes or [],
        routes=routes or [],
    )


class TestDeadCodeDetector:
    async def test_unused_import_detected(self) -> None:
        pf = _make_pf(
            path="src/app.py",
            content="import os\nimport sys\n\ndef hello():\n    print('hello')\n",
            imports=[ParsedImport(name="os", line=1), ParsedImport(name="sys", line=2)],
            functions=[ParsedFunction(name="hello", line_start=4, line_end=5, calls=["print"])],
            function_calls=[{"name": "print"}],
        )
        detector = DeadCodeDetector([pf])
        results = await detector.detect_all()
        unused = [r for r in results if r.code_type == "unused_import"]
        assert len(unused) == 2
        assert unused[0].name == "os"
        assert unused[1].name == "sys"

    async def test_used_import_not_reported(self) -> None:
        pf = _make_pf(
            path="src/app.py",
            content="import os\n\nprint(os.getcwd())\n",
            imports=[ParsedImport(name="os", line=1)],
            functions=[],
            function_calls=[{"name": "print"}],
        )
        detector = DeadCodeDetector([pf])
        results = await detector.detect_all()
        unused = [r for r in results if r.code_type == "unused_import"]
        assert len(unused) == 0

    async def test_unused_function_detected(self) -> None:
        pf = _make_pf(
            path="src/utils.py",
            content="def helper():\n    pass\n\ndef used():\n    pass\n",
            functions=[
                ParsedFunction(name="helper", line_start=1, line_end=2),
                ParsedFunction(name="used", line_start=4, line_end=5),
            ],
            function_calls=[{"name": "used"}],
        )
        detector = DeadCodeDetector([pf])
        results = await detector.detect_all()
        unused_funcs = [r for r in results if r.code_type == "unused_function"]
        assert len(unused_funcs) == 1
        assert unused_funcs[0].name == "helper"

    async def test_entry_point_function_not_reported(self) -> None:
        pf = _make_pf(
            path="src/routes.py",
            content="def get_users():\n    pass\n",
            functions=[ParsedFunction(name="get_users", line_start=1, line_end=2, decorators=["@app.get"])],
            routes=[],
        )
        detector = DeadCodeDetector([pf])
        results = await detector.detect_all()
        unused_funcs = [r for r in results if r.code_type == "unused_function"]
        assert len(unused_funcs) == 0

    async def test_orphan_class_detected(self) -> None:
        pf = _make_pf(
            path="src/models.py",
            content="class OldModel:\n    pass\n",
            classes=[__import__("app.domain.contracts.parser", fromlist=["ParsedClass"]).ParsedClass(
                name="OldModel", line_start=1, line_end=2,
            )],
        )
        detector = DeadCodeDetector([pf])
        results = await detector.detect_all()
        orphans = [r for r in results if r.code_type == "orphan_class"]
        assert len(orphans) == 1
        assert orphans[0].name == "OldModel"

    async def test_empty_parsed_files(self) -> None:
        detector = DeadCodeDetector([])
        results = await detector.detect_all()
        assert results == []

    async def test_unused_variable_detected(self) -> None:
        content = "def foo():\n    x = 42\n    return 'hello'\n"
        pf = _make_pf(
            path="src/app.py",
            content=content,
            functions=[ParsedFunction(name="foo", line_start=1, line_end=3)],
        )
        detector = DeadCodeDetector([pf])
        results = await detector.detect_all()
        unused_vars = [r for r in results if r.code_type == "unused_variable"]
        assert len(unused_vars) == 1
        assert unused_vars[0].name == "x"

    async def test_unreachable_code_detected(self) -> None:
        content = "def foo():\n    return 'done'\n    x = 42\n"
        pf = _make_pf(
            path="src/app.py",
            content=content,
            functions=[ParsedFunction(name="foo", line_start=1, line_end=3)],
        )
        detector = DeadCodeDetector([pf])
        results = await detector.detect_all()
        unreachable = [r for r in results if r.code_type == "unreachable_code"]
        assert len(unreachable) >= 1

    async def test_confidence_scores(self) -> None:
        pf = _make_pf(
            path="src/app.py",
            content="import unused_lib\n\ndef helper():\n    pass\n",
            imports=[ParsedImport(name="unused_lib", line=1)],
            functions=[ParsedFunction(name="helper", line_start=3, line_end=4)],
        )
        detector = DeadCodeDetector([pf])
        results = await detector.detect_all()
        for r in results:
            assert 0 <= r.confidence <= 1.0
