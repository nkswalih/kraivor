import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class TypeScriptParser(AbstractParser):
    language: str = "typescript"
    supported_extensions: list[str] = [".ts", ".tsx"]

    _FUNC_DECL = re.compile(
        r"(?:export\s+)?(?:async\s+)?function\s+\*?\s*(\w+)\s*\("
    )
    _ARROW_FUNC = re.compile(
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|\w+)\s*=>"
    )
    _CLASS_DECL = re.compile(
        r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+(\w+(?:\s*,\s*\w+)*))?"
    )
    _IMPORT_DEFAULT = re.compile(
        r"import\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']"
    )
    _IMPORT_NAMED = re.compile(
        r"import\s+\{\s*([^}]+)\s*\}\s+from\s+[\"']([^\"']+)[\"']"
    )
    _IMPORT_STAR = re.compile(
        r"import\s+\*\s+as\s+(\w+)\s+from\s+[\"']([^\"']+)[\"']"
    )
    _IMPORT_SIDE_EFFECT = re.compile(
        r"import\s+[\"']([^\"']+)[\"']"
    )
    _REQUIRE = re.compile(
        r"(?:const|let|var)\s+(?:(\w+)|\{\s*([^}]+)\s*\})\s*=\s*require\([\"']([^\"']+)[\"']\)"
    )
    _EXPORT_DEFAULT = re.compile(r"export\s+default\s+(\w+)")
    _EXPORT_NAMED = re.compile(r"export\s+\{\s*([^}]+)\s*\}")
    _EXPORT_DECL = re.compile(
        r"export\s+(const|let|var|function|class|interface|type|enum)\s+(\w+)"
    )
    _EXPORT_MODULE = re.compile(r"module\.exports\s*=")
    _EXPORT_NAMED_ASSIGN = re.compile(r"exports\.(\w+)\s*=")
    _EXPRESS_ROUTE = re.compile(
        r"(?:app|router|route|server|fastify|api)\.(get|post|put|delete|patch|options|all|head)\([\"']([^\"']+)[\"']"
    )
    _COMPLEXITY_KEYWORDS = re.compile(
        r"\b(?:if|for|while|switch|case|catch)\b"
    )
    _JSX_TAG = re.compile(r"<[A-Z][\w.]*(?:\s+\w+\s*=|/>)|</[A-Z]")

    _INTERFACE_DECL = re.compile(
        r"(?:export\s+)?(?:abstract\s+)?interface\s+(\w+)(?:\s+extends\s+(\w+(?:\s*,\s*\w+)*))?"
    )
    _ENUM_DECL = re.compile(
        r"(?:export\s+)?(?:const\s+)?enum\s+(\w+)"
    )
    _TYPE_ALIAS = re.compile(
        r"(?:export\s+)?type\s+(\w+)(?:<[^>]+>)?\s*="
    )
    _DECORATOR = re.compile(r"@(\w+(?:\.\w+)?)\s*(?:\([^)]*\))?")
    _NESTJS_ROUTE = re.compile(
        r"@(?:Get|Post|Put|Delete|Patch|Options|Head|All)(?:\([\"']([^\"']+)[\"']\)|\(\))"
    )

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        parsed = ParsedFile(
            path=file_path,
            language=self.language,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            lines_count=content.count("\n") + 1,
        )

        self._extract_functions(content, parsed)
        self._extract_classes(content, parsed)
        self._extract_imports(content, parsed)
        self._extract_exports(content, parsed)
        self._extract_routes(content, parsed)
        self._detect_jsx(content, parsed)
        self._extract_interfaces(content, parsed)
        self._extract_enums(content, parsed)
        self._extract_type_aliases(content, parsed)
        self._extract_decorators(content, parsed)
        self._extract_nestjs_routes(content, parsed)

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

        for match in self._ARROW_FUNC.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            parsed.functions.append(
                ParsedFunction(name=name, line_start=line_start, line_end=line_start, complexity=1)
            )

    def _extract_classes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._CLASS_DECL.finditer(content):
            name = match.group(1)
            bases = []
            if match.group(2):
                bases.append(match.group(2))
            if match.group(3):
                bases.extend(b.strip() for b in match.group(3).split(","))
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            body = content[body_start + 1 : body_end]
            line_end = content[:body_end].count("\n") + 1

            method_names = []
            clean_body = re.sub(r"^\s*@\w+(?:\([^)]*\))?\s*$", "", body, flags=re.MULTILINE)
            no_decorator_body = re.sub(r"@\w+(?:\([^)]*\))?", "", clean_body)
            for m in re.finditer(
                r"^\s*(?:(?:public|private|protected|static|readonly|async)\s+)*(\w+)\s*\([^)]*\)\s*(?:\{|\:)", no_decorator_body, re.MULTILINE
            ):
                method_name = m.group(1)
                if method_name not in {"if", "for", "while", "switch", "catch", "with"}:
                    method_names.append(method_name)

            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    bases=bases,
                    methods=method_names,
                )
            )

    def _extract_imports(self, content: str, parsed: ParsedFile) -> None:
        for match in self._IMPORT_DEFAULT.finditer(content):
            name, source = match.group(1), match.group(2)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(name=name, source=source, line=line, is_from=True)
            )

        for match in self._IMPORT_NAMED.finditer(content):
            names_str = match.group(1)
            if names_str and names_str.strip():
                names = [n.strip().split(" as ")[0].strip() for n in names_str.split(",")]
                source = match.group(2)
                line = content[: match.start()].count("\n") + 1
                for name in names:
                    if name:
                        parsed.imports.append(
                            ParsedImport(name=name, source=source, line=line, is_from=True)
                        )

        for match in self._IMPORT_STAR.finditer(content):
            name, source = match.group(1), match.group(2)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(name=f"* as {name}", source=source, line=line, is_from=True)
            )

        for match in self._IMPORT_SIDE_EFFECT.finditer(content):
            source = match.group(1)
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(
                ParsedImport(name="", source=source, line=line, is_from=True)
            )

        for match in self._REQUIRE.finditer(content):
            source = match.group(3)
            line = content[: match.start()].count("\n") + 1
            if match.group(1):
                parsed.imports.append(
                    ParsedImport(name=match.group(1), source=source, line=line, is_from=False)
                )
            elif match.group(2):
                names = [n.strip().split(":")[0].strip() for n in match.group(2).split(",")]
                for name in names:
                    parsed.imports.append(
                        ParsedImport(name=name, source=source, line=line, is_from=False)
                    )

        # import type { X } from 'y'
        for match in re.finditer(
            r"import\s+type\s+\{\s*([^}]+)\s*\}\s+from\s+[\"']([^\"']+)[\"']", content
        ):
            names = [n.strip() for n in match.group(1).split(",")]
            source = match.group(2)
            line = content[: match.start()].count("\n") + 1
            for name in names:
                if name:
                    parsed.imports.append(
                        ParsedImport(name=name, source=source, line=line, is_from=True)
                    )

    def _extract_exports(self, content: str, parsed: ParsedFile) -> None:
        for match in self._EXPORT_DEFAULT.finditer(content):
            parsed.exports.append(f"default {match.group(1)}")

        for match in self._EXPORT_NAMED.finditer(content):
            names = [n.strip() for n in match.group(1).split(",")]
            parsed.exports.extend(names)

        for match in self._EXPORT_DECL.finditer(content):
            parsed.exports.append(match.group(2))

        for match in self._EXPORT_MODULE.finditer(content):
            parsed.exports.append("module.exports")

        for match in self._EXPORT_NAMED_ASSIGN.finditer(content):
            parsed.exports.append(match.group(1))

    def _extract_routes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._EXPRESS_ROUTE.finditer(content):
            method, path = match.group(1).upper(), match.group(2)
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method, handler_name="", line_start=line_start, line_end=line_start)
            )

    def _detect_jsx(self, content: str, parsed: ParsedFile) -> None:
        if self._JSX_TAG.search(content):
            parsed.ast_data["jsx"] = True

    def _extract_interfaces(self, content: str, parsed: ParsedFile) -> None:
        for match in self._INTERFACE_DECL.finditer(content):
            name = match.group(1)
            bases = []
            if match.group(2):
                bases.extend(b.strip() for b in match.group(2).split(","))
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            body = content[body_start + 1 : body_end]
            line_end = content[:body_end].count("\n") + 1

            properties = []
            for m in re.finditer(
                r"^\s*(\w+)\??\s*(?:\?)?\s*:", body, re.MULTILINE
            ):
                properties.append(m.group(1))

            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    bases=bases,
                    decorators=["interface"],
                    methods=properties,
                )
            )

    def _extract_enums(self, content: str, parsed: ParsedFile) -> None:
        for match in self._ENUM_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            body = content[body_start + 1 : body_end]
            line_end = content[:body_end].count("\n") + 1

            members = []
            for m in re.finditer(r"^\s*(\w+)", body, re.MULTILINE):
                members.append(m.group(1))

            parsed.classes.append(
                ParsedClass(
                    name=name,
                    line_start=line_start,
                    line_end=line_end,
                    decorators=["enum"],
                    methods=members,
                )
            )

    def _extract_type_aliases(self, content: str, parsed: ParsedFile) -> None:
        for match in self._TYPE_ALIAS.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1
            line_end = content[: match.end()].count("\n") + 1
            parsed.exports.append(f"type {name}")

    def _extract_decorators(self, content: str, parsed: ParsedFile) -> None:
        decorators = set()
        for match in self._DECORATOR.finditer(content):
            decorators.add(match.group(1))
        if decorators:
            parsed.ast_data["decorators"] = sorted(decorators)

    def _extract_nestjs_routes(self, content: str, parsed: ParsedFile) -> None:
        for match in self._NESTJS_ROUTE.finditer(content):
            path = match.group(1) if match.group(1) else "/"
            method = match.group(0).lstrip("@").split("(")[0].upper()
            line_start = content[: match.start()].count("\n") + 1
            parsed.routes.append(
                ParsedRoute(path=path, method=method, handler_name="", line_start=line_start, line_end=line_start)
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
        complexity += len(TypeScriptParser._COMPLEXITY_KEYWORDS.findall(body))
        complexity += len(re.findall(r"&&", body))
        complexity += len(re.findall(r"\|\|", body))
        return complexity
