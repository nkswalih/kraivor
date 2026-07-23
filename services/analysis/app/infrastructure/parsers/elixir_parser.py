import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class ElixirParser(AbstractParser):
    language: str = "elixir"
    supported_extensions: list[str] = [".ex", ".exs"]

    _MODULE_DECL = re.compile(r"defmodule\s+(\w+(?:\.\w+)*)\s+do")
    _DEF_DECL = re.compile(r"def(?:p|macro|guard)?\s+(\w+)\s*\(([^)]*)\)")
    _DEF_IMPLICIT = re.compile(r"def(?:p|macro|guard)?\s+(\w+)(?!\s*\()")
    _ALIAS = re.compile(r"alias\s+(\w+(?:\.\w+)*)")
    _IMPORT = re.compile(r"import\s+(\w+(?:\.\w+)*)")
    _USE = re.compile(r"use\s+(\w+(?:\.\w+)*)")
    _REQUIRE = re.compile(r"require\s+(\w+(?:\.\w+)*)")
    _STRUCT = re.compile(r"defstruct\s+(\[[^\]]*\])")
    _PHOENIX_ROUTE_GET = re.compile(
        r"get\s+[\"']([^\"']+)[\"']\s*,\s*(\w+(?:\.\w+)?(?:,\s*\[?:?\w+\])?)"
    )
    _PHOENIX_ROUTE_POST = re.compile(
        r"post\s+[\"']([^\"']+)[\"']\s*,\s*(\w+(?:\.\w+)?)"
    )
    _PHOENIX_ROUTE_PUT = re.compile(r"put\s+[\"']([^\"']+)[\"']\s*,\s*(\w+(?:\.\w+)?)")
    _PHOENIX_ROUTE_PATCH = re.compile(
        r"patch\s+[\"']([^\"']+)[\"']\s*,\s*(\w+(?:\.\w+)?)"
    )
    _PHOENIX_ROUTE_DELETE = re.compile(
        r"delete\s+[\"']([^\"']+)[\"']\s*,\s*(\w+(?:\.\w+)?)"
    )
    _PHOENIX_RESOURCES = re.compile(r"resources\s+[\"']([^\"']+)[\"']")
    _COMPLEXITY_KW = re.compile(r"\b(?:if|unless|cond|case|for|try|catch|rescue)\b")
    _PIPE = re.compile(r"\s\|>\s")

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        parsed = ParsedFile(
            path=file_path,
            language=self.language,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            lines_count=len(content.splitlines()) if content else 0,
        )

        self._extract_imports(content, parsed)
        self._extract_modules(content, parsed)
        self._extract_functions(content, parsed)
        self._extract_routes(content, parsed)

        return parsed

    def _extract_imports(self, content: str, parsed: ParsedFile) -> None:
        for match in self._ALIAS.finditer(content):
            source = match.group(1)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(
                    name="", source=source, line=line, is_from=False, alias="alias"
                )
            )

        for match in self._IMPORT.finditer(content):
            source = match.group(1)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(
                    name="", source=source, line=line, is_from=False, alias="import"
                )
            )

        for match in self._REQUIRE.finditer(content):
            source = match.group(1)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(
                    name="", source=source, line=line, is_from=False, alias="require"
                )
            )

        for match in self._USE.finditer(content):
            source = match.group(1)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(
                    name="", source=source, line=line, is_from=False, alias="use"
                )
            )

    def _extract_modules(self, content: str, parsed: ParsedFile) -> None:
        for match in self._MODULE_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("do", match.end())
            if body_start == -1:
                continue
            body_end = self._find_module_end(content, body_start)
            line_end = content[:body_end].count("\n") + 1

            func_names = []
            for m in self._DEF_DECL.finditer(content[body_start:body_end]):
                func_names.append(m.group(1))

            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    decorators=["module"],
                    methods=func_names,
                )
            )

    def _extract_functions(self, content: str, parsed: ParsedFile) -> None:
        for match in self._DEF_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            body = self._extract_function_body(content, match.end())
            line_end = line_start + body.count("\n")
            parsed.functions.append(
                ParsedFunction(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    complexity=self._calculate_complexity(body),
                )
            )

    def _extract_routes(self, content: str, parsed: ParsedFile) -> None:
        for pattern, method in [
            (self._PHOENIX_ROUTE_GET, "GET"),
            (self._PHOENIX_ROUTE_POST, "POST"),
            (self._PHOENIX_ROUTE_PUT, "PUT"),
            (self._PHOENIX_ROUTE_PATCH, "PATCH"),
            (self._PHOENIX_ROUTE_DELETE, "DELETE"),
        ]:
            for match in pattern.finditer(content):
                path = match.group(1)
                handler = (
                    match.group(2) if match.lastindex and match.lastindex >= 2 else ""
                )
                line_start = content[: match.start()].count("\n") + 1
                parsed.routes.append(
                    ParsedRoute(
                        path=path,
                        method=method,
                        handler_name=handler,
                        line_start=line_start,
                        line_end=line_start,
                    )
                )

        for match in self._PHOENIX_RESOURCES.finditer(content):
            path = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(
                    path=path,
                    method="RESOURCE",
                    handler_name="",
                    line_start=line_start,
                    line_end=line_start,
                )
            )

    def _extract_function_body(self, content: str, start_pos: int) -> str:
        lines = content[start_pos:].split("\n")
        body_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith("def")
                or stripped.startswith("defp")
                or stripped.startswith("defmacro")
            ):
                break
            body_lines.append(line)
        return "\n".join(body_lines)

    @staticmethod
    def _find_module_end(content: str, start_pos: int) -> int:
        lines = content[start_pos:].split("\n")
        depth = 1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (
                stripped.startswith("defmodule ")
                or stripped.startswith("def ")
                or stripped.startswith("defp ")
            ):
                depth += 1
            if stripped == "end":
                depth -= 1
                if depth == 0:
                    return start_pos + sum(len(line) + 1 for line in lines[: i + 1])
        return start_pos + len(content) - 1

    @staticmethod
    def _calculate_complexity(body: str) -> int:
        complexity = 1
        complexity += len(ElixirParser._COMPLEXITY_KW.findall(body))
        complexity += len(ElixirParser._PIPE.findall(body))
        return complexity
