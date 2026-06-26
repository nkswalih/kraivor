import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class GoParser(AbstractParser):
    language: str = "go"
    supported_extensions: list[str] = [".go"]

    _FUNC_DECL = re.compile(
        r"func\s+(?:\([^)]*\)\s+)?(\w+)\s*\("
    )
    _STRUCT_DECL = re.compile(
        r"type\s+(\w+)\s+struct\s*\{"
    )
    _INTERFACE_DECL = re.compile(
        r"type\s+(\w+)\s+interface\s*\{"
    )
    _TYPE_ALIAS = re.compile(
        r"type\s+(\w+)\s+(?!struct|interface)"
    )
    _IMPORT_SINGLE = re.compile(
        r'import\s+[\'"]([^\'"]+)[\'"]'
    )
    _IMPORT_MULTI = re.compile(
        r'\s+[\'"]([^\'"]+)[\'"]'
    )
    _GIN_ROUTE = re.compile(
        r"(?:r|router|engine|g)\.(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|Any|StaticFile|Static)\([\"']([^\"']+)[\"']"
    )
    _FIBER_ROUTE = re.compile(
        r"(?:app|f)\.(?:Get|Post|Put|Delete|Patch|Head|Options|All|Static)\([\"']([^\"']+)[\"']"
    )
    _ECHO_ROUTE = re.compile(
        r"(?:e|echo|g)\.(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|Any)\([\"']([^\"']+)[\"']"
    )
    _COMPLEXITY_KEYWORDS = re.compile(
        r"\b(?:if|for|switch|select|range)\b"
    )
    _CASE_KEYWORD = re.compile(r"\bcase\s")

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        parsed = ParsedFile(
            path=file_path,
            language=self.language,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            lines_count=content.count("\n") + 1,
        )

        self._extract_functions(content, parsed)
        self._extract_structs(content, parsed)
        self._extract_interfaces(content, parsed)
        self._extract_imports(content, parsed)
        self._extract_routes(content, parsed)

        return parsed

    def _extract_functions(self, content: str, parsed: ParsedFile) -> None:
        for match in self._FUNC_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            body = self._extract_body(content, match.end())
            line_end = line_start + body.count("\n")
            parsed.functions.append(
                ParsedFunction(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    complexity=self._calculate_complexity(body),
                )
            )

    def _extract_structs(self, content: str, parsed: ParsedFile) -> None:
        for match in self._STRUCT_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("{", match.end() - 1)
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            body = content[body_start + 1 : body_end]
            line_end = content[:body_end].count("\n") + 1

            fields = []
            for m in re.finditer(r"^\s+(\w+)\s+", body, re.MULTILINE):
                fields.append(m.group(1))

            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    decorators=["struct"],
                    methods=fields,
                )
            )

    def _extract_interfaces(self, content: str, parsed: ParsedFile) -> None:
        for match in self._INTERFACE_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("{", match.end() - 1)
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            body = content[body_start + 1 : body_end]
            line_end = content[:body_end].count("\n") + 1

            methods = []
            for m in re.finditer(r"^\s+(\w+)\([^)]*\)", body, re.MULTILINE):
                methods.append(m.group(1))

            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    decorators=["interface"],
                    methods=methods,
                )
            )

    def _extract_imports(self, content: str, parsed: ParsedFile) -> None:
        for match in self._IMPORT_SINGLE.finditer(content):
            source = match.group(1)
            import_line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(name="", source=source, line=import_line, is_from=False)
            )

        in_import_block = False
        for line_no, line in enumerate(content.split("\n"), start=1):
            stripped = line.strip()
            if stripped == "import (":
                in_import_block = True
                continue
            if in_import_block and stripped == ")":
                in_import_block = False
                continue
            if in_import_block:
                source = stripped.strip('"')
                if source:
                    parsed.imports.append(
                        ParsedImport(name="", source=source, line=line_no, is_from=False)
                    )

    def _extract_routes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._GIN_ROUTE.finditer(content):
            path = match.group(1)
            method = match.group(0).split(".")[1].split("(")[0]
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method.upper(), handler_name="", line_start=line_start, line_end=line_start)
            )

        for match in self._FIBER_ROUTE.finditer(content):
            path = match.group(1)
            method = match.group(0).split(".")[1].split("(")[0]
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method.upper(), handler_name="", line_start=line_start, line_end=line_start)
            )

        for match in self._ECHO_ROUTE.finditer(content):
            path = match.group(1)
            method = match.group(0).split(".")[1].split("(")[0]
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method.upper(), handler_name="", line_start=line_start, line_end=line_start)
            )

    def _extract_body(self, content: str, start_pos: int) -> str:
        brace_pos = content.find("{", start_pos)
        if brace_pos == -1:
            return ""
        end_pos = self._find_matching_brace(content, brace_pos)
        return content[brace_pos : end_pos + 1]

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
        complexity += len(GoParser._COMPLEXITY_KEYWORDS.findall(body))
        complexity += len(GoParser._CASE_KEYWORD.findall(body))
        return complexity
