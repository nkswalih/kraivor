import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class RustParser(AbstractParser):
    language: str = "rust"
    supported_extensions: list[str] = [".rs"]

    _STRUCT_DECL = re.compile(
        r"(?:pub\s+)?struct\s+(\w+)(?:<[^>]*>)?(?:\s*\{|;)",
    )
    _ENUM_DECL = re.compile(
        r"(?:pub\s+)?enum\s+(\w+)(?:<[^>]*>)?\s*\{",
    )
    _TRAIT_DECL = re.compile(
        r"(?:pub\s+)?(?:unsafe\s+)?trait\s+(\w+)(?:<[^>]*>)?(?:\s*:\s*([^{]+?))?(?=\s*\{)",
    )
    _IMPL_DECL = re.compile(
        r"(?:pub\s+)?(?:unsafe\s+)?impl\s+(?:<[^>]*>\s+)?(?:\w+(?:<[^>]*>)?\s+for\s+)?(\w+(?:<[^>]*>)?)\s*\{",
    )
    _FN_DECL = re.compile(
        r'(?:pub\s+)?(?:async\s+)?(?:unsafe\s+)?(?:extern\s+"[^"]+"\s+)?fn\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*[^{;]+)?(?:\s*where\s+[^{;]+)?(?=\s*\{|\s*;)',
        re.MULTILINE,
    )
    _USE = re.compile(
        r"use\s+(?:pub\s+)?(?:\w+(?:::\w+)*(?:::\*)?(?:\s+as\s+\w+)?)\s*;",
    )
    _USE_PATH = re.compile(
        r"use\s+(?:pub\s+)?([\w:*]+(?:\s+as\s+\w+)?)\s*;",
    )
    _MOD_DECL = re.compile(
        r"(?:pub\s+)?mod\s+(\w+)\s*(?:;|\{)",
    )
    _MACRO = re.compile(
        r"(\w+)!\s*",
    )
    _COMPLEXITY_KW = re.compile(
        r"\b(?:if|else|for|while|loop|match|catch)\b",
    )

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        parsed = ParsedFile(
            path=file_path,
            language=self.language,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            lines_count=len(content.splitlines()) if content else 0,
        )

        self._extract_imports(content, parsed)
        self._extract_structs(content, parsed)
        self._extract_enums(content, parsed)
        self._extract_traits(content, parsed)
        self._extract_functions(content, parsed)

        return parsed

    def _extract_imports(self, content: str, parsed: ParsedFile) -> None:
        for match in self._USE_PATH.finditer(content):
            source = match.group(1).strip()
            line = content[: match.start()].count("\n") + 1
            parsed.imports.append(ParsedImport(name="", source=source, line=line, is_from=False))

    def _extract_structs(self, content: str, parsed: ParsedFile) -> None:
        for match in self._STRUCT_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1

            body_start = content.find("{", match.end())
            if body_start == -1:
                line_end = line_start
            else:
                body_end = self._find_matching_brace(content, body_start)
                line_end = content[:body_end].count("\n") + 1

            parsed.classes.append(
                ParsedClass(name=name, line_start=line_start, line_end=line_end, decorators=["struct"])
            )

    def _extract_enums(self, content: str, parsed: ParsedFile) -> None:
        for match in self._ENUM_DECL.finditer(content):
            name = match.group(1)
            line_start = content[: match.start()].count("\n") + 1

            body_start = match.end() - 1
            body_end = self._find_matching_brace(content, body_start)
            line_end = content[:body_end].count("\n") + 1

            variants = []
            for v in re.finditer(r"^\s*(\w+)", content[body_start + 1 : body_end], re.MULTILINE):
                variants.append(v.group(1))

            parsed.classes.append(
                ParsedClass(name=name, line_start=line_start, line_end=line_end, decorators=["enum"], methods=variants)
            )

    def _extract_traits(self, content: str, parsed: ParsedFile) -> None:
        for match in self._TRAIT_DECL.finditer(content):
            name = match.group(1)
            bases: list[str] = []
            if match.group(2):
                bases.extend(b.strip() for b in match.group(2).split("+") if b.strip())

            line_start = content[: match.start()].count("\n") + 1
            body_start = content.find("{", match.end())
            if body_start == -1:
                continue
            body_end = self._find_matching_brace(content, body_start)
            line_end = content[:body_end].count("\n") + 1

            parsed.classes.append(
                ParsedClass(name=name, line_start=line_start, line_end=line_end, bases=bases, decorators=["trait"])
            )

    def _extract_functions(self, content: str, parsed: ParsedFile) -> None:
        for match in self._FN_DECL.finditer(content):
            name, params = match.group(1), match.group(2)
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
                ParsedFunction(name=name, line_start=line_start, line_end=line_end, complexity=complexity)
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
        complexity += len(RustParser._COMPLEXITY_KW.findall(body))
        complexity += len(re.findall(r"=>", body))
        complexity += len(re.findall(r"&&", body))
        complexity += len(re.findall(r"\|\|", body))
        return complexity
