import re

from app.core.constants import ErrorType
from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile

logger = get_logger(__name__)


class ErrorFinding:
    def __init__(
        self,
        error_type: str,
        severity: str,
        title: str,
        description: str,
        file_path: str,
        line_start: int | None = None,
        line_end: int | None = None,
        code_snippet: str | None = None,
        recommendation: str | None = None,
    ) -> None:
        self.error_type = error_type
        self.severity = severity
        self.title = title
        self.description = description
        self.file_path = file_path
        self.line_start = line_start
        self.line_end = line_end
        self.code_snippet = code_snippet
        self.recommendation = recommendation

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": None,
            "repo_id": None,
            "workspace_id": None,
            "error_type": self.error_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
        }


class ErrorScanner:
    def __init__(self, parsed_files: list[ParsedFile]) -> None:
        self.parsed_files = parsed_files

    async def scan_all(self) -> list[ErrorFinding]:
        results: list[ErrorFinding] = []
        for pf in self.parsed_files:
            content = pf.content
            file_path = pf.path
            file_results = await self._scan_file(file_path, content)
            results.extend(file_results)
        return results

    async def _scan_file(self, file_path: str, content: str) -> list[ErrorFinding]:
        findings: list[ErrorFinding] = []
        findings.extend(self._detect_bare_except(file_path, content))
        findings.extend(self._detect_swallowed_exceptions(file_path, content))
        findings.extend(self._detect_missing_timeouts(file_path, content))
        findings.extend(self._detect_silent_failures(file_path, content))
        return findings

    def _detect_bare_except(self, file_path: str, content: str) -> list[ErrorFinding]:
        findings: list[ErrorFinding] = []
        pattern = re.compile(r"^\s*except\s*:", re.MULTILINE)
        for match in pattern.finditer(content):
            line_num = content[: match.start()].count("\n") + 1
            lines = content.split("\n")
            start = max(0, line_num - 3)
            end = min(len(lines), line_num + 5)
            snippet = "\n".join(lines[start:end])
            findings.append(
                ErrorFinding(
                    error_type=ErrorType.BARE_EXCEPT,
                    severity="high",
                    title="Bare except clause catches all exceptions",
                    description="'except:' without an exception type catches EVERY exception, "
                    "including SystemExit and KeyboardInterrupt. This can mask "
                    "critical errors and make debugging impossible.",
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num,
                    code_snippet=snippet,
                    recommendation="Use 'except Exception as e:' instead of bare 'except:'. "
                    "Catch only the exceptions you can handle.",
                )
            )
        return findings

    def _detect_swallowed_exceptions(
        self, file_path: str, content: str
    ) -> list[ErrorFinding]:
        findings: list[ErrorFinding] = []
        pattern = re.compile(
            r"except\s+(\w+(?:\s*,\s*\w+)*)\s*:\s*\n\s*pass",
            re.MULTILINE,
        )
        for match in pattern.finditer(content):
            line_num = content[: match.start()].count("\n") + 1
            exc_type = match.group(1)
            findings.append(
                ErrorFinding(
                    error_type=ErrorType.SWALLOWED_EXCEPTION,
                    severity="critical" if "Exception" in exc_type else "high",
                    title="Exception swallowed with 'pass'",
                    description=f"Exception '{exc_type}' is caught but ignored. "
                    "The system continues running in an error state.",
                    file_path=file_path,
                    line_start=line_num,
                    recommendation="Handle the exception appropriately: log it, "
                    "return an error response, or recover the state. "
                    "Never 'pass' on exceptions.",
                )
            )
        return findings

    def _detect_missing_timeouts(
        self, file_path: str, content: str
    ) -> list[ErrorFinding]:
        findings: list[ErrorFinding] = []
        http_patterns = [
            r"requests\.(?:get|post|put|delete|patch)\(",
            r"httpx\.(?:get|post|put|delete|patch)\(",
            r"aiohttp\.ClientSession\(\)",
            r"urllib\.request\.urlopen\(",
            r"httpx\.AsyncClient\(",
        ]
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern_str in http_patterns:
                if re.search(pattern_str, line) and "timeout" not in line.lower():
                    findings.append(
                        ErrorFinding(
                            error_type=ErrorType.MISSING_TIMEOUT,
                            severity="high",
                            title="External HTTP call without timeout",
                            description="This external HTTP call has no timeout configured. "
                            "If the remote service is slow, this request will "
                            "block indefinitely and exhaust the connection pool.",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Add timeout parameter: requests.get(url, timeout=5)",
                        )
                    )
        return findings

    def _detect_silent_failures(
        self, file_path: str, content: str
    ) -> list[ErrorFinding]:
        findings: list[ErrorFinding] = []
        pattern = re.compile(
            r"except\s+(\w+(?:\s*,\s*\w+)*)\s*:\s*\n\s*(?:log|logger|logging|print)(?:\.\w+)?\s*\(",
            re.MULTILINE,
        )
        for match in pattern.finditer(content):
            line_num = content[: match.start()].count("\n") + 1
            exc_type = match.group(1)
            findings.append(
                ErrorFinding(
                    error_type=ErrorType.SILENT_FAIL,
                    severity="medium",
                    title="Exception logged but not handled",
                    description=f"Exception '{exc_type}' is caught but only logged. "
                    "The system continues running in an inconsistent state.",
                    file_path=file_path,
                    line_start=line_num,
                    recommendation="After logging, handle the exception: return an error "
                    "response, recover state, or re-raise if appropriate.",
                )
            )
        return findings
