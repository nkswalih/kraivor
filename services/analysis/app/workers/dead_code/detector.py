import re
from collections.abc import Sequence

from app.core.constants import DeadCodeType
from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile

logger = get_logger(__name__)


class DeadCodeFinding:
    def __init__(
        self,
        code_type: str,
        name: str,
        file_path: str,
        line_start: int | None = None,
        line_end: int | None = None,
        context: str | None = None,
        evidence: str | None = None,
        confidence: float = 0.0,
    ) -> None:
        self.code_type = code_type
        self.name = name
        self.file_path = file_path
        self.line_start = line_start
        self.line_end = line_end
        self.context = context
        self.evidence = evidence
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "job_id": None,
            "repo_id": None,
            "workspace_id": None,
            "code_type": self.code_type,
            "name": self.name,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "context": self.context,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


class DeadCodeDetector:
    def __init__(self, parsed_files: list[ParsedFile]) -> None:
        self.parsed_files = parsed_files
        self.entry_points: set[str] = set()
        self.dead_code: list[DeadCodeFinding] = []

    async def detect_all(self) -> list[DeadCodeFinding]:
        self._identify_entry_points()
        self._detect_unused_imports()
        self._detect_unused_functions()
        self._detect_unused_variables()
        self._detect_orphan_classes()
        self._detect_unreachable_code()
        return self.dead_code

    def _identify_entry_points(self) -> None:
        for pf in self.parsed_files:
            for func in pf.functions:
                for dec in func.decorators:
                    if any(kw in dec.lower() for kw in ("route", "app.", "router.", "api.", "celery", "task", "on_")):
                        self.entry_points.add(f"{func.name}:{pf.path}")
            for route in pf.routes:
                self.entry_points.add(f"{route.handler_name}:{pf.path}")
            for exp in pf.exports:
                self.entry_points.add(f"{exp}:{pf.path}")

    def _detect_unused_imports(self) -> None:
        for pf in self.parsed_files:
            content = pf.content
            lines = content.split("\n")
            for imp in pf.imports:
                import_name = imp.name.split(".")[0] if "." in imp.name else imp.name
                import_line = imp.line
                usage_found = False
                for line_num, line in enumerate(lines, 1):
                    if line_num <= import_line:
                        continue
                    pattern = rf'(?<![a-zA-Z_]){re.escape(import_name)}(?![a-zA-Z_])'
                    if re.search(pattern, line):
                        usage_found = True
                        break
                alias = imp.alias
                if alias and not usage_found:
                    for line_num, line in enumerate(lines, 1):
                        if line_num <= import_line:
                            continue
                        pattern = rf'(?<![a-zA-Z_]){re.escape(alias)}(?![a-zA-Z_])'
                        if re.search(pattern, line):
                            usage_found = True
                            break
                if not usage_found:
                    ctx_start = max(0, import_line - 2)
                    ctx_end = min(len(lines), import_line + 1)
                    self.dead_code.append(DeadCodeFinding(
                        code_type=DeadCodeType.UNUSED_IMPORT,
                        name=import_name,
                        file_path=pf.path,
                        line_start=import_line,
                        context="\n".join(lines[ctx_start:ctx_end]),
                        evidence=f"Import '{import_name}' is never used in this file",
                        confidence=0.95,
                    ))

    def _detect_unused_functions(self) -> None:
        all_functions: dict[str, ParsedFile] = {}
        func_name_to_path: dict[str, list[tuple[str, int, int]]] = {}
        for pf in self.parsed_files:
            for func in pf.functions:
                key = f"{func.name}:{pf.path}"
                all_functions[key] = pf
                func_name_to_path.setdefault(func.name, []).append((pf.path, func.line_start, func.line_end))

        all_calls: set[str] = set()
        for pf in self.parsed_files:
            for call in pf.function_calls:
                name = call.get("name", "") if isinstance(call, dict) else str(call)
                if name:
                    all_calls.add(name)
            for func in pf.functions:
                for call in func.calls:
                    if call:
                        all_calls.add(call)

        for func_key, pf in all_functions.items():
            func_name = func_key.split(":")[0]
            if func_key in self.entry_points:
                continue
            if func_name in all_calls:
                continue
            for fp, ls, le in func_name_to_path.get(func_name, []):
                if fp == pf.path:
                    self.dead_code.append(DeadCodeFinding(
                        code_type=DeadCodeType.UNUSED_FUNCTION,
                        name=func_name,
                        file_path=fp,
                        line_start=ls,
                        line_end=le,
                        evidence=f"Function '{func_name}' is defined but never called",
                        confidence=0.90,
                    ))

    def _detect_unused_variables(self) -> None:
        for pf in self.parsed_files:
            content = pf.content
            assign_pattern = re.compile(r'^\s+(\w+)\s*=\s*', re.MULTILINE)
            for match in assign_pattern.finditer(content):
                var_name = match.group(1)
                if var_name.startswith("_") or var_name.isupper():
                    continue
                lines = content.split("\n")
                assign_line = content[:match.start()].count("\n") + 1
                usage_found = False
                for ln, line in enumerate(lines, 1):
                    if ln <= assign_line:
                        continue
                    var_pattern = rf'(?<![a-zA-Z_]){re.escape(var_name)}(?![a-zA-Z_])'
                    if re.search(var_pattern, line):
                        usage_found = True
                        break
                if not usage_found:
                    self.dead_code.append(DeadCodeFinding(
                        code_type=DeadCodeType.UNUSED_VARIABLE,
                        name=var_name,
                        file_path=pf.path,
                        line_start=assign_line,
                        evidence=f"Variable '{var_name}' is assigned but never used",
                        confidence=0.85,
                    ))

    def _detect_orphan_classes(self) -> None:
        all_classes: dict[str, list[tuple[str, ParsedFile]]] = {}
        for pf in self.parsed_files:
            for cls in pf.classes:
                all_classes.setdefault(cls.name, []).append((pf.path, pf))

        for pf in self.parsed_files:
            content = pf.content
            lines = content.split("\n")
            for cls in pf.classes:
                if f"{cls.name}:{pf.path}" in self.entry_points:
                    continue
                usages = 0
                for ln, line in enumerate(lines, 1):
                    if cls.line_start and ln == cls.line_start:
                        continue
                    class_ref_pattern = re.compile(rf'(?<![a-zA-Z_.]){re.escape(cls.name)}(?![a-zA-Z_])')
                    if class_ref_pattern.search(line):
                        usages += 1
                import_usages = 0
                for imp in pf.imports:
                    if cls.name in imp.name or cls.name in imp.alias:
                        import_usages += 1
                if usages <= import_usages:
                    self.dead_code.append(DeadCodeFinding(
                        code_type=DeadCodeType.ORPHAN_CLASS,
                        name=cls.name,
                        file_path=pf.path,
                        line_start=cls.line_start,
                        line_end=cls.line_end,
                        evidence=f"Class '{cls.name}' is defined but may be unused",
                        confidence=0.75,
                    ))

    def _detect_unreachable_code(self) -> None:
        unreachable_patterns = [
            re.compile(r'return\s+.*\n\s+(?!return|raise|pass|$)'),
        ]
        for pf in self.parsed_files:
            content = pf.content
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("return") or stripped.startswith("raise"):
                    if i < len(lines):
                        next_line = lines[i]
                        next_stripped = next_line.strip()
                        indent_match = re.match(r'^(\s*)', line)
                        next_indent_match = re.match(r'^(\s*)', next_line)
                        if (indent_match and next_indent_match
                                and len(next_indent_match.group(1)) >= len(indent_match.group(1))
                                and next_stripped
                                and not next_stripped.startswith(("return", "raise", "pass", "#", "def ", "class ", "@", "except", "finally"))):
                            self.dead_code.append(DeadCodeFinding(
                                code_type=DeadCodeType.UNREACHABLE_CODE,
                                name="unreachable_statement",
                                file_path=pf.path,
                                line_start=i + 1,
                                evidence=f"Code after '{stripped.split(' ')[0]}' on line {i} is unreachable",
                                confidence=0.95,
                            ))
