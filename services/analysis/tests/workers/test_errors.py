from app.domain.contracts.parser import ParsedFile
from app.workers.errors.scanner import ErrorScanner


def _make_pf(path: str, content: str) -> ParsedFile:
    return ParsedFile(
        path=path,
        language="python",
        content=content,
        size_bytes=len(content),
        lines_count=len(content.split("\n")),
    )


class TestErrorScanner:
    async def test_bare_except_detected(self) -> None:
        content = """try:
    do_something()
except:
    pass
"""
        pf = _make_pf("app.py", content)
        scanner = ErrorScanner([pf])
        results = await scanner.scan_all()
        bare = [r for r in results if r.error_type == "bare_except"]
        assert len(bare) == 1
        assert "bare" in bare[0].title.lower()

    async def test_swallowed_exception_detected(self) -> None:
        content = """try:
    do_something()
except Exception:
    pass
"""
        pf = _make_pf("app.py", content)
        scanner = ErrorScanner([pf])
        results = await scanner.scan_all()
        swallowed = [r for r in results if r.error_type == "swallowed_exception"]
        assert len(swallowed) == 1
        assert "Exception" in swallowed[0].title

    async def test_missing_timeout_detected(self) -> None:
        content = """def fetch():
    response = requests.get('https://example.com')
    return response.json()
"""
        pf = _make_pf("app.py", content)
        scanner = ErrorScanner([pf])
        results = await scanner.scan_all()
        timeout = [r for r in results if r.error_type == "missing_timeout"]
        assert len(timeout) >= 1

    async def test_request_with_timeout_not_reported(self) -> None:
        content = """def fetch():
    response = requests.get('https://example.com', timeout=5)
    return response.json()
"""
        pf = _make_pf("app.py", content)
        scanner = ErrorScanner([pf])
        results = await scanner.scan_all()
        timeout = [r for r in results if r.error_type == "missing_timeout"]
        assert len(timeout) == 0

    async def test_silent_failure_detected(self) -> None:
        content = """try:
    do_something()
except Exception:
    logger.error("failed")
"""
        pf = _make_pf("app.py", content)
        scanner = ErrorScanner([pf])
        results = await scanner.scan_all()
        silent = [r for r in results if r.error_type == "silent_fail"]
        assert len(silent) >= 1

    async def test_clean_code_no_findings(self) -> None:
        content = """def hello():
    return "world"
"""
        pf = _make_pf("app.py", content)
        scanner = ErrorScanner([pf])
        results = await scanner.scan_all()
        assert len(results) == 0

    async def test_empty_file(self) -> None:
        pf = _make_pf("app.py", "")
        scanner = ErrorScanner([pf])
        results = await scanner.scan_all()
        assert results == []

    async def test_httpx_missing_timeout(self) -> None:
        content = """async def fetch():
    async with httpx.AsyncClient() as client:
        resp = await client.get('https://example.com')
    return resp
"""
        pf = _make_pf("app.py", content)
        scanner = ErrorScanner([pf])
        results = await scanner.scan_all()
        timeout = [r for r in results if r.error_type == "missing_timeout"]
        assert len(timeout) >= 1
