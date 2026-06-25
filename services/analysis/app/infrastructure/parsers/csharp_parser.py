import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class CSharpParser(AbstractParser):
    language: str = "csharp"
    supported_extensions: list[str] = [".cs"]

    _CLASS_DECL = re.compile(
        r"(?:public|private|protected|internal|static|abstract|sealed|partial|readonly)\s+(?:class|struct)\s+(\w+)(?:\s*:\s*([^{]+?))?(?:\s*where\s+\w+\s*:.*?)?(?=\s*\{)",
        re.DOTALL,
    )
    _METHOD_DECL = re.compile(
        r"(?:public|private|protected|internal|static|virtual|override|abstract|async|unsafe|sealed|new|extern|partial|readonly)\s+(?:async\s+)?(?:\w+(?:<[^>]*>)?\.\w+\s+)?(\w+(?:<[^>]*>)?)\s+(\w+(?:<[^>]*>)?)\s*\(([^)]*)\)\s*(?:\{|=>)",
        re.MULTILINE,
    )
    _INTERFACE_DECL = re.compile(
        r"(?:public|private|protected|internal)?\s*interface\s+(\w+)(?:\s*:\s*([^{]+?))?(?=\s*\{)"
    )
    _RECORD_DECL = re.compile(
        r"(?:public|private|protected|internal|sealed|abstract|readonly)?\s*record\s+(?:class|struct)?\s*(\w+)(?:<[^>]*>)?(?:\s*:\s*([^{]+?))?(?:\s*\{|\()"
    )
    _PROPERTY_DECL = re.compile(
        r"(?:public|private|protected|internal|static|virtual|override|new|required|readonly)\s+(\w+(?:<[^>]*>)?(?:\?|\[\])?)\s+(\w+)\s*\{\s*(?:get|set|init)\s*(?:;\s*(?:get|set|init)\s*)*;?\s*\}"
    )
    _USING = re.compile(
        r"using\s+(?:static\s+)?([\w.]+(?:\.\*)?)\s*(?:=\s*\w+)?\s*;"
    )
    _ROUTE = re.compile(
        r"\[Http(Get|Post|Put|Delete|Patch|Options|Head)"
        r"(?:\s*\(\s*[\"']([^\"']+)[\"']?\s*\))?\]"
    )
    _MINIMAL_ROUTE = re.compile(
        r"(?:app|builder)\.(?:MapGet|MapPost|MapPut|MapDelete|MapPatch|MapMethods)\([\"']([^\"']+)[\"']"
    )
    _ATTRIBUTE = re.compile(r"\[(\w+(?:\([^)]*\))?)\]")
    _COMPLEXITY_KW = re.compile(
        r"\b(?:if|for|foreach|while|switch|case|catch)\b"
    )

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        parsed = ParsedFile(
            path=file_path,
            language=self.language,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            lines_count=len(content.splitlines()) if content else 0,
        )

        self._extract_usings(content, parsed)
        self._extract_classes(content, parsed)
        self._extract_interfaces(content, parsed)
        self._extract_records(content, parsed)
        self._extract_methods(content, parsed)
        self._extract_properties(content, parsed)
        self._extract_routes(content, parsed)

        return parsed

    def _extract_usings(self, content: str, parsed: ParsedFile) -> None:
        for match in self._USING.finditer(content):
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
                bases = [b.strip() for b in match.group(2).split(",") if b.strip()]

            line_start = content[: match.start()].count("\n") + 1
            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            line_end = content[:body_end].count("\n") + 1

            method_names = []
            for m in self._METHOD_DECL.finditer(content[body_start:body_end]):
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
                bases = [b.strip() for b in match.group(2).split(",") if b.strip()]

            line_start = content[: match.start()].count("\n") + 1
            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            line_end = content[:body_end].count("\n") + 1

            sigs = []
            for sig_match in re.finditer(r"(\w+)\s*\([^)]*\)\s*;", content[body_start:body_end], re.MULTILINE):
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

    def _extract_records(self, content: str, parsed: ParsedFile) -> None:
        for match in self._RECORD_DECL.finditer(content):
            name = match.group(1)
            bases: list[str] = []
            if match.group(2):
                bases = [b.strip() for b in match.group(2).split(",") if b.strip()]

            line_start = content[: match.start()].count("\n") + 1
            line_end = line_start
            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    bases=bases,
                    decorators=["record"],
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

            parsed.functions.append(
                ParsedFunction(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    complexity=complexity,
                    calls=[p.strip() for p in params.split(",") if p.strip()],
                )
            )

    def _extract_properties(self, content: str, parsed: ParsedFile) -> None:
        for match in self._PROPERTY_DECL.finditer(content):
            prop_type, name = match.group(1), match.group(2)
            line_start = content[: match.start()].count("\n") + 1
            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_start,
                    decorators=["property", prop_type],
                )
            )

    def _extract_routes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._ROUTE.finditer(content):
            method = match.group(1).upper()
            path = match.group(2) if match.group(2) else "/"
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method, handler_name="", line_start=line_start, line_end=line_start)
            )

        for match in self._MINIMAL_ROUTE.finditer(content):
            path = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            method_str = match.group(0).split(".")[1].split("(")[0].upper()
            parsed.routes.append(
                ParsedRoute(path=path, method=method_str, handler_name="", line_start=line_start, line_end=line_start)
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
        complexity += len(CSharpParser._COMPLEXITY_KW.findall(body))
        complexity += len(re.findall(r"&&", body))
        complexity += len(re.findall(r"\|\|", body))
        complexity += len(re.findall(r"\?\s", body))
        return complexity
