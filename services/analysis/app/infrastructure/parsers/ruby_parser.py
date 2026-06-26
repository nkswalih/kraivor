import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class RubyParser(AbstractParser):
    language: str = "ruby"
    supported_extensions: list[str] = [".rb"]

    _CLASS_DECL = re.compile(
        r"class\s+(\w+(?:::\w+)*)(?:\s*<\s*(\w+(?:::\w+)*))?(?=\s*$|\s*\n|\s*#)",
        re.MULTILINE,
    )
    _MODULE_DECL = re.compile(
        r"module\s+(\w+(?:::\w+)*)(?=\s*$|\s*\n)",
    )
    _METHOD_DECL = re.compile(
        r"(?:def\s+)(?:self\.)?(\w+(?:[?!]|[=])?)\s*(?:\(([^)]*)\))?\s*$",
        re.MULTILINE,
    )
    _RAILS_ROUTE = re.compile(
        r"(?:get|post|put|patch|delete)\s+[\"']([^\"']+)[\"']\s*=>\s*[\"'](\w+#\w+)[\"']",
    )
    _RAILS_ROUTE_BLOCK = re.compile(
        r"(?:get|post|put|patch|delete)\s+[\"']([^\"']+)[\"'](?:\s*,\s*(?:to:\s*[\"'](\w+#\w+)[\"']|controller:\s*[\"'](\w+)[\"']))?",
    )
    _REQUIRE = re.compile(
        r"require(?:_relative)?\s+[\"']([^\"']+)[\"']",
    )
    _INCLUDE = re.compile(
        r"include\s+(\w+(?:::\w+)*)",
    )
    _EXTEND = re.compile(
        r"extend\s+(\w+(?:::\w+)*)",
    )
    _ATTR_ACCESSOR = re.compile(
        r"attr_(?:accessor|reader|writer)\s+(?::(\w+)(?:\s*,\s*:(\w+))*)",
    )
    _COMPLEXITY_KW = re.compile(
        r"\b(?:if|elsif|unless|for|while|until|case|when|catch|rescue)\b",
    )

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        parsed = ParsedFile(
            path=file_path,
            language=self.language,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            lines_count=len(content.splitlines()) if content else 0,
        )

        self._extract_requires(content, parsed)
        self._extract_modules(content, parsed)
        self._extract_classes(content, parsed)
        self._extract_methods(content, parsed)
        self._extract_routes(content, parsed)

        return parsed

    def _extract_requires(self, content: str, parsed: ParsedFile) -> None:
        for match in self._REQUIRE.finditer(content):
            source = match.group(1)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(ParsedImport(name="", source=source, line=line, is_from=False))

    def _extract_modules(self, content: str, parsed: ParsedFile) -> None:
        for match in self._MODULE_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            parsed.classes.append(
                ParsedClass(name=name, line_start=line_start, line_end=line_start, decorators=["module"])
            )

    def _extract_classes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._CLASS_DECL.finditer(content):
            name = match.group(1)
            bases: list[str] = [match.group(2)] if match.group(2) else []
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("def ", match.end())
            if body_start == -1:
                body_end = line_start
            else:
                body_end = self._find_class_end(content, body_start)

            method_names = []
            for m in self._METHOD_DECL.finditer(content[match.end():body_end]):
                method_names.append(m.group(1))

            parsed.classes.append(
                ParsedClass(name=name, line_start=line_start, line_end=body_end, bases=bases, methods=method_names)
            )

    def _extract_methods(self, content: str, parsed: ParsedFile) -> None:
        for match in self._METHOD_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            body = self._extract_method_body(content, match.end())
            line_end = line_start + body.count("\n")
            parsed.functions.append(
                ParsedFunction(name=name, line_start=line_start, line_end=line_end, complexity=self._calculate_complexity(body))
            )

    def _extract_routes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._RAILS_ROUTE.finditer(content):
            path = match.group(1)
            handler = match.group(2)
            method = match.group(0).split()[0].upper()
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method, handler_name=handler, line_start=line_start, line_end=line_start)
            )

        for match in self._RAILS_ROUTE_BLOCK.finditer(content):
            path = match.group(1)
            method = match.group(0).split()[0].upper()
            handler = match.group(2) or ""
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method, handler_name=handler, line_start=line_start, line_end=line_start)
            )

    def _extract_method_body(self, content: str, start_pos: int) -> str:
        lines = content[start_pos:].split("\n")
        body_lines: list[str] = []
        indent: str | None = None
        for line in lines:
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#"):
                body_lines.append(stripped)
                continue
            if indent is None and stripped.startswith((" ", "\t")):
                indent = line[:len(line) - len(line.lstrip())]
                body_lines.append(stripped)
            elif indent is not None and not stripped.startswith((" ", "\t")):
                break
            elif indent is not None:
                body_lines.append(stripped)
            elif indent is None and not stripped.startswith((" ", "\t")):
                if stripped.strip() == "end":
                    break
        return "\n".join(body_lines)

    @staticmethod
    def _find_class_end(content: str, start_pos: int) -> int:
        lines = content[start_pos:].split("\n")
        depth = 1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("class ") or stripped.startswith("module ") or stripped.startswith("def "):
                depth += 1
            elif stripped == "end":
                depth -= 1
                if depth == 0:
                    return start_pos + sum(len(line) + 1 for line in lines[:i + 1])
        return start_pos + len(content) - 1

    @staticmethod
    def _calculate_complexity(body: str) -> int:
        complexity = 1
        complexity += len(RubyParser._COMPLEXITY_KW.findall(body))
        complexity += len(re.findall(r"&&", body))
        complexity += len(re.findall(r"\|\|", body))
        return complexity
