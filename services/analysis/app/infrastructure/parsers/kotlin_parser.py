import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class KotlinParser(AbstractParser):
    language: str = "kotlin"
    supported_extensions: list[str] = [".kt", ".kts"]

    _CLASS_DECL = re.compile(
        r"(?:data\s+|sealed\s+|open\s+|abstract\s+|inner\s+|value\s+)?(?:class|object)\s+(\w+)(?:<[^>]*>)?(?:\s*\(\s*([^)]*)\s*\))?(?:\s*:\s*([^{]+?))?(?=\s*\{|\s*\(|$)",
        re.MULTILINE,
    )
    _INTERFACE_DECL = re.compile(
        r"(?:fun\s+)?interface\s+(\w+)(?:<[^>]*>)?(?:\s*:\s*([^{]+?))?(?=\s*\{)"
    )
    _FUNCTION_DECL = re.compile(
        r"(?:(?:public|private|protected|internal|open|override|abstract|suspend|inline|tailrec|external|infix|operator)\s+)?(?:fun\s+)(?:<[^>]+>\s+)?(\w+)\s*\(([^)]*)\)\s*(?::\s*[^{]+)?(?=\s*\{|=)",
        re.MULTILINE,
    )
    _PROPERTY_DECL = re.compile(
        r"(?:public|private|protected|internal|open|override|lateinit|val|var)\s+(?:val|var)\s+(\w+)\s*(?::\s*\w+(?:<[^>]*>)?(?:\?)?)?\s*(?:=\s*[^,;\n]+|get\s*\(\)|set\s*\([^)]*\))?"
    )
    _IMPORT = re.compile(r"import\s+([\w.*]+)\s*")
    _PACKAGE = re.compile(r"package\s+([\w.]+)\s*")
    _ANNOTATION = re.compile(r"@(\w+(?:\([^)]*\))?)")
    _KTOR_ROUTE = re.compile(
        r"(?:routing\s*\{[\s\S]*?)(get|post|put|delete|patch)\s*\{\s*"
    )
    _KTOR_ROUTE_SIMPLE = re.compile(
        r"(?:get|post|put|delete|patch)\s*\(\s*[\"']([^\"']+)[\"']\s*\)"
    )
    _SPRING_BOOT_ROUTE = re.compile(
        r"@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)"
        r"(?:\(\s*(?:value\s*=\s*)?[\"']([^\"']+)[\"']\s*\))?"
    )
    _COMPLEXITY_KW = re.compile(r"\b(?:if|for|while|when|catch)\b")

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
        self._extract_functions(content, parsed)
        self._extract_routes(content, parsed)

        return parsed

    def _extract_package(self, content: str, parsed: ParsedFile) -> None:
        match = self._PACKAGE.search(content)
        if match:
            parsed.imports.append(
                ParsedImport(
                    name="package", source=match.group(1), line=1, is_from=False
                )
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
                bases.extend(b.strip() for b in match.group(2).split(",") if b.strip())

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

    def _extract_functions(self, content: str, parsed: ParsedFile) -> None:
        for match in self._FUNCTION_DECL.finditer(content):
            name, _params = match.group(1), match.group(2)
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("{", match.end())
            if body_start == -1:
                body_start = content.find("=", match.end())
                if body_start == -1:
                    line_end = line_start
                    complexity = 1
                else:
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
        for match in self._SPRING_BOOT_ROUTE.finditer(content):
            method_str = match.group(1).upper().replace("MAPPING", "")
            path = match.group(2) if match.group(2) else "/"
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(
                    path=path,
                    method=method_str,
                    handler_name="",
                    line_start=line_start,
                    line_end=line_start,
                )
            )

        for match in self._KTOR_ROUTE_SIMPLE.finditer(content):
            path = match.group(1)
            method = match.group(0).split("(")[0].upper()
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
        complexity += len(KotlinParser._COMPLEXITY_KW.findall(body))
        complexity += len(re.findall(r"&&", body))
        complexity += len(re.findall(r"\|\|", body))
        return complexity
