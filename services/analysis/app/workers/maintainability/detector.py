import re

from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile
from app.workers.maintainability.models import (
    MaintainabilityFinding,
    MaintainabilityMetrics,
)

logger = get_logger(__name__)

_EFFORT_ESTIMATES: dict[str, float] = {
    "long_method": 2.0,
    "too_many_parameters": 0.5,
    "high_cyclomatic_complexity": 3.0,
    "deep_nesting": 2.0,
    "duplicate_code": 4.0,
    "large_class": 3.0,
    "too_many_methods": 2.0,
    "long_line": 0.25,
    "missing_docstring": 0.5,
    "magic_number": 0.25,
    "empty_catch_block": 1.0,
    "todo_comment": 0.25,
    "deep_inheritance": 3.0,
    "circular_import": 2.0,
}


class MaintainabilityDetector:
    def __init__(self, parsed_files: list[ParsedFile]) -> None:
        self.parsed_files = parsed_files

    async def scan_all(self) -> list[MaintainabilityFinding]:
        results: list[MaintainabilityFinding] = []
        for pf in self.parsed_files:
            content = pf.content
            file_path = pf.path
            results.extend(self._detect_long_methods(pf))
            results.extend(self._detect_too_many_parameters(pf))
            results.extend(self._detect_high_cyclomatic_complexity(pf))
            results.extend(self._detect_deep_nesting(file_path, content))
            results.extend(self._detect_duplicate_code(file_path, content))
            results.extend(self._detect_large_class(pf))
            results.extend(self._detect_too_many_methods(pf))
            results.extend(self._detect_long_lines(file_path, content))
            results.extend(self._detect_missing_docstrings(pf, file_path))
            results.extend(self._detect_magic_numbers(file_path, content))
            results.extend(self._detect_empty_catch_blocks(file_path, content))
            results.extend(self._detect_todo_comments(file_path, content))
            results.extend(self._detect_deep_inheritance(pf, file_path))
            results.extend(self._detect_circular_imports(file_path, content))
        return results

    def compute_metrics(
        self, findings: list[MaintainabilityFinding]
    ) -> MaintainabilityMetrics:
        total = len(findings)
        if total == 0:
            return MaintainabilityMetrics()

        total_files = max(1, len(self.parsed_files))
        complexity_violations = sum(
            1
            for f in findings
            if f.maintainability_type
            in ("high_cyclomatic_complexity", "deep_nesting", "deep_inheritance")
        )
        long_methods_count = sum(
            1 for f in findings if f.maintainability_type == "long_method"
        )
        deep_nesting_count = sum(
            1 for f in findings if f.maintainability_type == "deep_nesting"
        )
        large_classes_count = sum(
            1 for f in findings if f.maintainability_type == "large_class"
        )

        maintainability_index = (
            100
            - (
                complexity_violations * 5
                + long_methods_count * 3
                + deep_nesting_count * 4
                + large_classes_count * 3
            )
            / total_files
        )
        maintainability_index = max(0.0, maintainability_index)

        technical_debt_hours = sum(
            _EFFORT_ESTIMATES.get(f.maintainability_type, 0.0) for f in findings
        )

        total_complexity = 0
        count_with_complexity = 0
        for pf in self.parsed_files:
            for func in pf.functions:
                total_complexity += (
                    func.complexity if hasattr(func, "complexity") else 0
                )
                count_with_complexity += 1
        if count_with_complexity > 0:
            avg_complexity = total_complexity / count_with_complexity
            complexity_score = max(0.0, 100.0 - avg_complexity * 5)
        else:
            complexity_score = 100.0

        return MaintainabilityMetrics(
            maintainability_index=round(maintainability_index, 2),
            technical_debt_hours=round(technical_debt_hours, 2),
            complexity_score=round(complexity_score, 2),
            total_findings=total,
        )

    def _detect_long_methods(self, pf: ParsedFile) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        for func in pf.functions:
            if hasattr(func, "line_start") and hasattr(func, "line_end"):
                length = func.line_end - func.line_start
                if length > 50:
                    content_lines = pf.content.split("\n")
                    snippet_lines = content_lines[
                        max(0, func.line_start - 1) : min(
                            len(content_lines), func.line_start + 2
                        )
                    ]
                    findings.append(
                        MaintainabilityFinding(
                            maintainability_type="long_method",
                            severity="medium",
                            title=f"Long method '{func.name}' ({length} lines)",
                            description=f"Method '{func.name}' is {length} lines long (threshold: 50). Long methods reduce readability and increase maintenance cost.",
                            file_path=pf.path,
                            line_start=func.line_start,
                            line_end=func.line_end,
                            code_snippet="\n".join(snippet_lines),
                            recommendation=f"Refactor '{func.name}' into smaller helper functions. Consider extracting logical blocks.",
                            confidence=0.9,
                            estimated_effort_hours=_EFFORT_ESTIMATES["long_method"],
                        )
                    )
        return findings

    def _detect_too_many_parameters(
        self, pf: ParsedFile
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        content_lines = pf.content.split("\n")
        for func in pf.functions:
            start = max(0, func.line_start - 1)
            sig_lines: list[str] = []
            for i in range(start, min(len(content_lines), start + 10)):
                line = content_lines[i]
                sig_lines.append(line)
                stripped = line.rstrip()
                if stripped.endswith(":"):
                    break

            sig = " ".join(sig_lines)
            match = re.search(r"def\s+\w+\s*\(([^)]*)\)", sig)
            if not match:
                continue
            params_str = match.group(1).strip()
            if not params_str:
                continue
            params = [
                p.strip()
                for p in params_str.split(",")
                if p.strip() and not p.strip().startswith(("*", "**"))
            ]
            params = [p for p in params if p not in ("self", "cls")]

            if len(params) > 5:
                snippet = (
                    content_lines[min(start, len(content_lines) - 1)].strip()
                    if content_lines
                    else ""
                )
                findings.append(
                    MaintainabilityFinding(
                        maintainability_type="too_many_parameters",
                        severity="medium",
                        title=f"Too many parameters in '{func.name}' ({len(params)})",
                        description=f"Function '{func.name}' has {len(params)} parameters (threshold: 5). Many parameters make the interface hard to use and test.",
                        file_path=pf.path,
                        line_start=func.line_start,
                        line_end=func.line_start,
                        code_snippet=snippet,
                        recommendation="Reduce parameters by using a configuration object, builder pattern, or keyword arguments.",
                        confidence=0.85,
                        estimated_effort_hours=_EFFORT_ESTIMATES["too_many_parameters"],
                    )
                )
        return findings

    def _detect_high_cyclomatic_complexity(
        self, pf: ParsedFile
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        for func in pf.functions:
            complexity = getattr(func, "complexity", 0)
            if complexity > 10:
                content_lines = pf.content.split("\n")
                snippet = ""
                if (
                    content_lines
                    and func.line_start > 0
                    and func.line_start <= len(content_lines)
                ):
                    snippet = content_lines[func.line_start - 1].strip()
                findings.append(
                    MaintainabilityFinding(
                        maintainability_type="high_cyclomatic_complexity",
                        severity="high",
                        title=f"High cyclomatic complexity in '{func.name}' ({complexity})",
                        description=f"Function '{func.name}' has cyclomatic complexity of {complexity} (threshold: 10). Complex code is harder to test and maintain.",
                        file_path=pf.path,
                        line_start=func.line_start,
                        line_end=func.line_end,
                        code_snippet=snippet,
                        recommendation=f"Simplify '{func.name}' by extracting conditionals into separate functions or using polymorphism.",
                        confidence=0.9,
                        estimated_effort_hours=_EFFORT_ESTIMATES[
                            "high_cyclomatic_complexity"
                        ],
                    )
                )
        return findings

    def _detect_deep_nesting(
        self, file_path: str, content: str
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        lines = content.split("\n")
        current_indent_level = 0
        nesting_depth = 0
        max_depth = 0
        max_depth_line = 0
        nesting_keywords = re.compile(
            r"(if |elif |else:|for |while |with |try:|except |finally:)"
        )

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())
            indent_level = indent // 4 if indent else 0

            if indent_level > current_indent_level:
                if nesting_keywords.search(stripped):
                    current_indent_level = indent_level
                    nesting_depth += 1
                    if nesting_depth > max_depth:
                        max_depth = nesting_depth
                        max_depth_line = line_num
            elif indent_level < current_indent_level:
                depth_diff = current_indent_level - indent_level
                nesting_depth = max(0, nesting_depth - depth_diff)
                current_indent_level = indent_level

        if max_depth > 4:
            snippet = ""
            if max_depth_line <= len(lines):
                snippet = lines[max_depth_line - 1].strip()
            findings.append(
                MaintainabilityFinding(
                    maintainability_type="deep_nesting",
                    severity="medium",
                    title=f"Deep nesting detected ({max_depth} levels)",
                    description=f"Code reaches {max_depth} levels of nesting (threshold: 4). Deeply nested code is hard to read and maintain.",
                    file_path=file_path,
                    line_start=max_depth_line,
                    line_end=max_depth_line,
                    code_snippet=snippet,
                    recommendation="Reduce nesting by extracting inner blocks into separate functions or using guard clauses.",
                    confidence=0.8,
                    estimated_effort_hours=_EFFORT_ESTIMATES["deep_nesting"],
                )
            )
        return findings

    def _detect_duplicate_code(
        self, file_path: str, content: str
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        lines = content.split("\n")
        seen_blocks: dict[str, list[int]] = {}

        for i in range(len(lines) - 2):
            block = "\n".join(lines[i : i + 3]).strip()
            if (
                len(block) < 20
                or block.startswith("#")
                or block.startswith("import")
                or block.startswith("from")
            ):
                continue
            normalized = re.sub(r"\s+", " ", block)
            if normalized not in seen_blocks:
                seen_blocks[normalized] = []
            seen_blocks[normalized].append(i + 1)

        for _normalized, positions in seen_blocks.items():
            if len(positions) >= 2:
                snippet = "\n".join(lines[positions[0] - 1 : positions[0] + 2]).strip()
                findings.append(
                    MaintainabilityFinding(
                        maintainability_type="duplicate_code",
                        severity="medium",
                        title=f"Duplicate code block found ({len(positions)} occurrences)",
                        description=f"A block of code appears {len(positions)} times (lines {positions}). Duplication increases maintenance effort.",
                        file_path=file_path,
                        line_start=positions[0],
                        line_end=positions[0] + 2,
                        code_snippet=snippet[:200],
                        recommendation="Extract the duplicated block into a shared function or module.",
                        confidence=0.7,
                        estimated_effort_hours=_EFFORT_ESTIMATES["duplicate_code"],
                    )
                )
                break
        return findings

    def _detect_large_class(self, pf: ParsedFile) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        for cls in pf.classes:
            length = cls.line_end - cls.line_start
            if length > 300:
                content_lines = pf.content.split("\n")
                snippet = ""
                if (
                    content_lines
                    and cls.line_start > 0
                    and cls.line_start <= len(content_lines)
                ):
                    snippet = content_lines[cls.line_start - 1].strip()
                findings.append(
                    MaintainabilityFinding(
                        maintainability_type="large_class",
                        severity="medium",
                        title=f"Large class '{cls.name}' ({length} lines)",
                        description=f"Class '{cls.name}' is {length} lines long (threshold: 300). Large classes violate the Single Responsibility Principle.",
                        file_path=pf.path,
                        line_start=cls.line_start,
                        line_end=cls.line_end,
                        code_snippet=snippet,
                        recommendation=f"Split '{cls.name}' into smaller, focused classes using composition.",
                        confidence=0.9,
                        estimated_effort_hours=_EFFORT_ESTIMATES["large_class"],
                    )
                )
        return findings

    def _detect_too_many_methods(self, pf: ParsedFile) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        for cls in pf.classes:
            num_methods = len(cls.methods)
            if num_methods > 15:
                content_lines = pf.content.split("\n")
                snippet = ""
                if (
                    content_lines
                    and cls.line_start > 0
                    and cls.line_start <= len(content_lines)
                ):
                    snippet = content_lines[cls.line_start - 1].strip()
                findings.append(
                    MaintainabilityFinding(
                        maintainability_type="too_many_methods",
                        severity="medium",
                        title=f"Too many methods in class '{cls.name}' ({num_methods})",
                        description=f"Class '{cls.name}' has {num_methods} methods (threshold: 15). Too many methods indicate low cohesion.",
                        file_path=pf.path,
                        line_start=cls.line_start,
                        line_end=cls.line_end,
                        code_snippet=snippet,
                        recommendation=f"Consider splitting '{cls.name}' into smaller classes by concern.",
                        confidence=0.8,
                        estimated_effort_hours=_EFFORT_ESTIMATES["too_many_methods"],
                    )
                )
        return findings

    def _detect_long_lines(
        self, file_path: str, content: str
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if len(line) > 120:
                findings.append(
                    MaintainabilityFinding(
                        maintainability_type="long_line",
                        severity="low",
                        title=f"Line exceeds 120 characters ({len(line)} chars)",
                        description=f"Line {line_num} is {len(line)} characters long. Long lines reduce readability.",
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip()[:200],
                        recommendation="Break the line into multiple shorter lines or extract sub-expressions.",
                        confidence=0.95,
                        estimated_effort_hours=_EFFORT_ESTIMATES["long_line"],
                    )
                )
        return findings

    def _detect_missing_docstrings(
        self, pf: ParsedFile, file_path: str
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        for func in pf.functions:
            name = getattr(func, "name", "")
            doc = getattr(func, "docstring", "")
            if name and not name.startswith("_") and not doc:
                findings.append(
                    MaintainabilityFinding(
                        maintainability_type="missing_docstring",
                        severity="low",
                        title=f"Missing docstring for public function '{name}'",
                        description=f"Public function '{name}' has no docstring. Public functions should document their purpose, parameters, and return values.",
                        file_path=file_path,
                        line_start=func.line_start,
                        line_end=func.line_start,
                        code_snippet=f"def {name}(...):",
                        recommendation=f"Add a docstring to '{name}' explaining its purpose, arguments, and return value.",
                        confidence=0.85,
                        estimated_effort_hours=_EFFORT_ESTIMATES["missing_docstring"],
                    )
                )
        for cls in pf.classes:
            name = getattr(cls, "name", "")
            doc = getattr(cls, "docstring", "")
            if name and not name.startswith("_") and not doc:
                findings.append(
                    MaintainabilityFinding(
                        maintainability_type="missing_docstring",
                        severity="low",
                        title=f"Missing docstring for public class '{name}'",
                        description=f"Public class '{name}' has no docstring. Classes should document their purpose and usage.",
                        file_path=file_path,
                        line_start=cls.line_start,
                        line_end=cls.line_start,
                        code_snippet=f"class {name}(...):",
                        recommendation=f"Add a docstring to '{name}' describing the class purpose and key attributes.",
                        confidence=0.85,
                        estimated_effort_hours=_EFFORT_ESTIMATES["missing_docstring"],
                    )
                )
        return findings

    def _detect_magic_numbers(
        self, file_path: str, content: str
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        lines = content.split("\n")
        common_pattern = re.compile(r"(?<!\w)(?<!\.)(?:0|[1-9]\d*)(?:\.\d+)?(?![\w\.])")
        excluded_context = re.compile(
            r"(?:range|step|slice|index|count|len|size|offset|limit|timeout|max|min|average|mean|sum|retries|port|version|__\w+__)\s*[=\(:]"
            r"|\b(?:0|1)\b"
            r"|#.*"
            r'|["\'].*["\']'
        )

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("#")
                or stripped.startswith("import")
                or stripped.startswith("from")
            ):
                continue
            if excluded_context.search(line):
                continue
            if re.search(r"(?:def |class )", stripped):
                continue
            matches = common_pattern.findall(stripped)
            for match in matches:
                try:
                    val = float(match)
                    if val == 0.0 or val == 1.0:
                        continue
                except ValueError:
                    continue
                if match.isdigit() and len(match) <= 1:
                    continue
                if match.isdigit() and int(match) in (0, 1, 200, 404, 500):
                    continue
                assignment_check = re.search(
                    r"(?:=|return|yield|if |elif |while |with |assert|raise)\s*"
                    rf"{re.escape(match)}\b",
                    stripped,
                )
                context_check = bool(
                    re.search(r"(?:def |class |#)", stripped)
                    or '"""' in stripped
                    or "'''" in stripped
                )
                if assignment_check and not context_check:
                    findings.append(
                        MaintainabilityFinding(
                            maintainability_type="magic_number",
                            severity="low",
                            title=f"Magic number '{match}' on line {line_num}",
                            description=f"Undocumented numeric literal '{match}' found. Magic numbers make code harder to understand and maintain.",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=stripped[:200],
                            recommendation=f"Replace '{match}' with a named constant (e.g., {match.upper() if match.isdigit() else match.replace('.', '_')} = {match}).",
                            confidence=0.6,
                            estimated_effort_hours=_EFFORT_ESTIMATES["magic_number"],
                        )
                    )
                    break
        return findings

    def _detect_empty_catch_blocks(
        self, file_path: str, content: str
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r"^except\s*:", stripped) or re.match(
                r"^except\s+\w+\s*:", stripped
            ):
                next_lines = "\n".join(lines[line_num : min(len(lines), line_num + 4)])
                if "pass" in next_lines[:20]:
                    findings.append(
                        MaintainabilityFinding(
                            maintainability_type="empty_catch_block",
                            severity="high",
                            title="Empty except block with pass",
                            description="Exception handler contains only 'pass', silently swallowing errors. This hides bugs and makes debugging difficult.",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=stripped,
                            recommendation="Log the exception or handle it appropriately. At minimum, log: logger.exception('...')",
                            confidence=0.9,
                            estimated_effort_hours=_EFFORT_ESTIMATES[
                                "empty_catch_block"
                            ],
                        )
                    )
        return findings

    def _detect_todo_comments(
        self, file_path: str, content: str
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        lines = content.split("\n")
        pattern = re.compile(r"(?i)(TODO|FIXME|HACK|XXX|WORKAROUND)")

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") or "#" in stripped:
                match = pattern.search(stripped)
                if match:
                    findings.append(
                        MaintainabilityFinding(
                            maintainability_type="todo_comment",
                            severity="low",
                            title=f"{match.group(1)} comment found on line {line_num}",
                            description=f"'{match.group(1)}' comment indicates incomplete or temporary code that should be addressed.",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=stripped[:200],
                            recommendation=f"Address the {match.group(1)} item: either complete the implementation or create a tracking issue.",
                            confidence=0.95,
                            estimated_effort_hours=_EFFORT_ESTIMATES["todo_comment"],
                        )
                    )
        return findings

    def _detect_deep_inheritance(
        self, pf: ParsedFile, file_path: str
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        for cls in pf.classes:
            bases = getattr(cls, "bases", [])
            depth = len(bases)
            if depth > 3:
                content_lines = pf.content.split("\n")
                snippet = ""
                if (
                    content_lines
                    and cls.line_start > 0
                    and cls.line_start <= len(content_lines)
                ):
                    snippet = content_lines[cls.line_start - 1].strip()
                findings.append(
                    MaintainabilityFinding(
                        maintainability_type="deep_inheritance",
                        severity="medium",
                        title=f"Deep inheritance in '{cls.name}' ({depth} levels)",
                        description=f"Class '{cls.name}' has inheritance depth of {depth} (threshold: 3). Deep hierarchies are fragile and hard to understand.",
                        file_path=file_path,
                        line_start=cls.line_start,
                        line_end=cls.line_end,
                        code_snippet=snippet,
                        recommendation="Prefer composition over inheritance. Extract shared behavior into mixins or use dependency injection.",
                        confidence=0.75,
                        estimated_effort_hours=_EFFORT_ESTIMATES["deep_inheritance"],
                    )
                )
        return findings

    def _detect_circular_imports(
        self, file_path: str, content: str
    ) -> list[MaintainabilityFinding]:
        findings: list[MaintainabilityFinding] = []
        lines = content.split("\n")
        inside_function = False
        func_start = 0
        import_pattern = re.compile(r"^(?:import |from )")

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            if re.match(r"^def\s+\w+\s*\(", stripped) or re.match(
                r"^async\s+def\s+\w+\s*\(", stripped
            ):
                inside_function = True
                func_start = line_num
                continue

            if inside_function and stripped and not line.startswith((" ", "\t")):
                inside_function = False
                continue

            if (
                inside_function
                and import_pattern.match(stripped)
                and "typing" not in stripped
                and "TYPE_CHECKING" not in stripped
            ):
                snippet = stripped[:200]
                findings.append(
                    MaintainabilityFinding(
                        maintainability_type="circular_import",
                        severity="medium",
                        title=f"Import inside function body on line {line_num}",
                        description=f"Import statement inside a function body (started at line {func_start}) may indicate a circular dependency workaround.",
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=snippet,
                        recommendation="Move imports to the top of the file. If circular imports are the issue, restructure the modules or use late-binding patterns.",
                        confidence=0.6,
                        estimated_effort_hours=_EFFORT_ESTIMATES["circular_import"],
                    )
                )
        return findings
