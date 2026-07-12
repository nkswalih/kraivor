import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class PhpParser(AbstractParser):
    language: str = "php"
    supported_extensions: list[str] = [".php"]

    _CLASS_DECL = re.compile(
        r"(?:abstract\s+|final\s+|readonly\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+?))?(?=\s*\{)",
        re.MULTILINE,
    )
    _INTERFACE_DECL = re.compile(
        r"interface\s+(\w+)(?:\s+extends\s+([^{]+?))?(?=\s*\{)"
    )
    _TRAIT_DECL = re.compile(r"trait\s+(\w+)(?=\s*\{)")
    _ENUM_DECL = re.compile(r"enum\s+(\w+)(?:\s*:\s*\w+)?(?=\s*\{)")
    _FUNCTION_DECL = re.compile(
        r"(?:public|private|protected|static|abstract|final)?\s*(?:static\s+)?(?:public|private|protected)?\s*(?:static\s+)?function\s+(\w+)\s*\("
    )
    _LARAVEL_ROUTE = re.compile(
        r"Route::(?:get|post|put|patch|delete|options|any|match|resource|group|redirect|permanentRedirect|view)\([\"']([^\"']+)[\"']"
    )
    _SYMFONY_ROUTE = re.compile(r"#\[Route\([\"']([^\"']+)[\"']")
    _USE_IMPORT = re.compile(r"use\s+([\w\\\\]+)(?:\s+as\s+(\w+))?\s*;")
    _NAMESPACE = re.compile(r"namespace\s+([\w\\\\]+)\s*;")
    _ATTRIBUTE = re.compile(r"#\[(\w+(?:\([^)]*\))?)\]")
    _COMPLEXITY_KW = re.compile(
        r"\b(?:if|elseif|for|foreach|while|switch|case|catch)\b"
    )

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        parsed = ParsedFile(
            path=file_path,
            language=self.language,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            lines_count=len(content.splitlines()) if content else 0,
        )

        self._extract_namespace(content, parsed)
        self._extract_imports(content, parsed)
        self._extract_classes(content, parsed)
        self._extract_interfaces(content, parsed)
        self._extract_traits(content, parsed)
        self._extract_enums(content, parsed)
        self._extract_functions(content, parsed)
        self._extract_routes(content, parsed)

        return parsed

    def _extract_namespace(self, content: str, parsed: ParsedFile) -> None:
        match = self._NAMESPACE.search(content)
        if match:
            parsed.imports.append(
                ParsedImport(
                    name="namespace", source=match.group(1), line=1, is_from=False
                )
            )

    def _extract_imports(self, content: str, parsed: ParsedFile) -> None:
        for match in self._USE_IMPORT.finditer(content):
            source = match.group(1).lstrip("\\")
            alias = match.group(2) or ""
            line = content[: match.start()].count("\n") + 1
            name = source.split("\\")[-1]
            parsed.imports.append(
                ParsedImport(
                    name=name, alias=alias, source=source, line=line, is_from=False
                )
            )

    def _extract_classes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._CLASS_DECL.finditer(content):
            name = match.group(1)
            bases: list[str] = []
            if match.group(2):
                bases.append(match.group(2))
            if match.group(3):
                bases.extend(b.strip() for b in match.group(3).split(",") if b.strip())

            line_start = content[: match.start()].count("\n") + 1
            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            line_end = content[:body_end].count("\n") + 1

            method_names = []
            for m in self._FUNCTION_DECL.finditer(content[body_start:body_end]):
                method_names.append(m.group(1))

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
                bases.extend(b.strip() for b in match.group(2).split("|") if b.strip())

            line_start = content[: match.start()].count("\n") + 1
            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            line_end = content[:body_end].count("\n") + 1

            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    bases=bases,
                    decorators=["interface"],
                )
            )

    def _extract_traits(self, content: str, parsed: ParsedFile) -> None:
        for match in self._TRAIT_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_start,
                    decorators=["trait"],
                )
            )

    def _extract_enums(self, content: str, parsed: ParsedFile) -> None:
        for match in self._ENUM_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_start,
                    decorators=["enum"],
                )
            )

    def _extract_functions(self, content: str, parsed: ParsedFile) -> None:
        for match in self._FUNCTION_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("{", match.end())
            if body_start == -1:
                line_end = line_start
                complexity = 1
            else:
                body_end = self._find_matching_brace(content, body_start)
                body = content[body_start : body_end + 1]
                line_end = content[:body_end].count("\n") + 1
                complexity = self._calculate_complexity(body)

            parsed.functions.append(
                ParsedFunction(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    complexity=complexity,
                )
            )

    def _extract_routes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._LARAVEL_ROUTE.finditer(content):
            path = match.group(1)
            method = match.group(0).split("::")[1].split("(")[0].upper()
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(
                    path=path,
                    method=method,
                    handler_name="",
                    line_start=line_start,
                    line_end=line_start,
                )
            )

        for match in self._SYMFONY_ROUTE.finditer(content):
            path = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(
                    path=path,
                    method="GET",
                    handler_name="",
                    line_start=line_start,
                    line_end=line_start,
                )
            )

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
        complexity += len(PhpParser._COMPLEXITY_KW.findall(body))
        complexity += len(re.findall(r"&&", body))
        complexity += len(re.findall(r"\|\|", body))
        return complexity
