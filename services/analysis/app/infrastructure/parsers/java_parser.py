import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class JavaParser(AbstractParser):
    language: str = "java"
    supported_extensions: list[str] = [".java"]

    _CLASS_DECL = re.compile(
        r"(?:public|private|protected|static|abstract|final|sealed|non-sealed|strictfp)\s+(?:static\s+)?(?:abstract\s+)?(?:final\s+)?(?:sealed\s+)?(?:class|enum|record)\s+(\w+)(?:<[^>]*>)?\s*(?:\([^)]*\))?\s*(?:extends\s+([\w.]+(?:\s*,\s*[\w.]+)*))?\s*(?:implements\s+([\w.]+(?:\s*,\s*[\w.]+)*))?\s*(?:\{)",
        re.MULTILINE,
    )
    _INTERFACE_DECL = re.compile(
        r"(?:public|private|protected|sealed|non-sealed)?\s*interface\s+(\w+)(?:<[^>]*>)?\s*(?:extends\s+([\w.]+(?:\s*,\s*[\w.]+)*))?\s*\{",
        re.MULTILINE,
    )
    _METHOD_DECL = re.compile(
        r"(?:public|private|protected|static|abstract|final|synchronized|native|default|sealed)\s+(?:static\s+)?(?:abstract\s+)?(?:final\s+)?(?:synchronized\s+)?(?:<[^>]+>\s+)?(\w+(?:<[^>]*>)?(?:\[\])*)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[\w.]+(?:\s*,\s*[\w.]+)*)?\s*(?:\{|;)",
        re.MULTILINE,
    )
    _ANNOTATION = re.compile(r"@(\w+(?:\([^)]*\))?)")
    _SPRING_ROUTE = re.compile(
        r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)"
        r"(?:\(\s*(?:value\s*=\s*)?[\"']([^\"']+)[\"']\s*\))?"
    )
    _IMPORT = re.compile(
        r"import\s+(?:static\s+)?([\w.*]+)\s*;"
    )
    _PACKAGE = re.compile(
        r"^package\s+([\w.]+)\s*;", re.MULTILINE
    )

    _COMPLEXITY_KW = re.compile(
        r"\b(?:if|for|while|do|switch|case|catch)\b"
    )

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        parsed = ParsedFile(
            path=file_path,
            language=self.language,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            lines_count=len(content.splitlines()) if content else 0,
        )

        self._extract_package(content, parsed)
        self._extract_imports(content, parsed)
        self._extract_classes(content, parsed)
        self._extract_interfaces(content, parsed)
        self._extract_methods(content, parsed)
        self._extract_routes(content, parsed)

        return parsed

    def _extract_package(self, content: str, parsed: ParsedFile) -> None:
        match = self._PACKAGE.search(content)
        if match:
            parsed.imports.append(
                ParsedImport(name="package", source=match.group(1), line=1, is_from=False)
            )

    def _extract_imports(self, content: str, parsed: ParsedFile) -> None:
        for match in self._IMPORT.finditer(content):
            source = match.group(1).rstrip(".")
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(name="", source=source, line=line, is_from=False)
            )

    def _extract_classes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._CLASS_DECL.finditer(content):
            name = match.group(1)
            bases: list[str] = []
            if match.group(2):
                bases.extend(b.strip() for b in match.group(2).split(",") if b.strip())
            if match.group(3):
                bases.extend(b.strip() for b in match.group(3).split(",") if b.strip())

            line_start = content[: match.start()].count("\n") + 1
            body_start = match.end() - 1
            body_end = self._find_matching_brace(content, body_start)
            line_end = content[:body_end].count("\n") + 1

            method_names = []
            for m in self._METHOD_DECL.finditer(content[body_start:body_end + 1]):
                method_names.append(m.group(2))

            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    bases=bases,
                    methods=method_names,
                )
            )

    def _extract_interfaces(self, content: str, parsed: ParsedFile) -> None:
        for match in self._INTERFACE_DECL.finditer(content):
            name = match.group(1)
            bases: list[str] = []
            if match.group(2):
                bases.extend(b.strip() for b in match.group(2).split(",") if b.strip())

            line_start = content[: match.start()].count("\n") + 1
            body_start = match.end() - 1
            body_end = self._find_matching_brace(content, body_start)
            line_end = content[:body_end].count("\n") + 1

            sigs = []
            for sig_match in re.finditer(
                r"(?:\w+(?:<[^>]*>)?(?:\[\])*\s+)?(\w+)\s*\([^)]*\)\s*;",
                content[body_start:body_end + 1],
                re.MULTILINE,
            ):
                sigs.append(sig_match.group(1))

            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    bases=bases,
                    decorators=["interface"],
                    methods=sigs,
                )
            )

    def _extract_methods(self, content: str, parsed: ParsedFile) -> None:
        for match in self._METHOD_DECL.finditer(content):
            return_type, name, params = match.group(1), match.group(2), match.group(3)

            line_start = content[: match.start()].count("\n") + 1
            body_start = content.find("{", match.start())
            if body_start == -1:
                line_end = line_start
                complexity = 1
            else:
                body_end = self._find_matching_brace(content, body_start)
                body = content[body_start : body_end + 1]
                line_end = content[:body_end].count("\n") + 1
                complexity = self._calculate_complexity(body)

            decorators = self._extract_decorators(content, match.start())

            parsed.functions.append(
                ParsedFunction(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    complexity=complexity,
                    decorators=decorators,
                    calls=[p.strip() for p in params.split(",") if p.strip()],
                )
            )

    def _extract_routes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._SPRING_ROUTE.finditer(content):
            method_str = match.group(1).upper().replace("MAPPING", "")
            path = match.group(2) if match.group(2) else "/"
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method_str, handler_name="", line_start=line_start, line_end=line_start)
            )

    @staticmethod
    def _extract_decorators(content: str, position: int) -> list[str]:
        decs: list[str] = []
        before = content[:position].rstrip()
        lines_before = before.split("\n")
        for line in reversed(lines_before):
            stripped = line.strip()
            if stripped.startswith("@"):
                decs.insert(0, stripped[1:])
            else:
                break
        return decs

    @staticmethod
    def _find_matching_brace(content: str, open_pos: int) -> int:
        depth = 1
        i = open_pos + 1
        while i < len(content) and depth > 0:
            if content[i] == "{":
                depth += 1
            elif content[i] == "}":
                depth -= 1
            i += 1
        return i - 1 if depth == 0 else len(content) - 1

    @staticmethod
    def _calculate_complexity(body: str) -> int:
        complexity = 1
        complexity += len(JavaParser._COMPLEXITY_KW.findall(body))
        complexity += len(re.findall(r"&&", body))
        complexity += len(re.findall(r"\|\|", body))
        complexity += len(re.findall(r"\?\s", body))
        return complexity
