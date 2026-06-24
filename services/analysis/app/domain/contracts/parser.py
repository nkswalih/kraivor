from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(kw_only=True)
class ParsedFunction:
    name: str
    line_start: int
    line_end: int
    complexity: int = 0
    docstring: str = ""
    decorators: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    has_return: bool = False
    has_yield: bool = False
    ast_node: Any = None


@dataclass(kw_only=True)
class ParsedRoute:
    path: str
    method: str
    handler_name: str
    line_start: int
    line_end: int
    has_auth: bool = False
    decorators: list[str] = field(default_factory=list)
    code: str = ""


@dataclass(kw_only=True)
class ParsedImport:
    name: str
    alias: str = ""
    source: str = ""
    line: int = 0
    is_from: bool = False


@dataclass(kw_only=True)
class ParsedClass:
    name: str
    line_start: int
    line_end: int
    bases: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    docstring: str = ""
    ast_node: Any = None


@dataclass(kw_only=True)
class ParsedFile:
    path: str
    language: str
    content: str
    size_bytes: int
    lines_count: int

    functions: list[ParsedFunction] = field(default_factory=list)
    classes: list[ParsedClass] = field(default_factory=list)
    routes: list[ParsedRoute] = field(default_factory=list)
    imports: list[ParsedImport] = field(default_factory=list)
    function_calls: list[dict] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)

    errors: list[str] = field(default_factory=list)
    ast_data: dict[str, Any] = field(default_factory=dict)


class AbstractParser(ABC):
    """Contract for language-specific code parsers.

    Implementations use tree-sitter, Python ast, or regex-based
    heuristics to extract structural information from source code.
    """

    language: str = ""
    supported_extensions: list[str] = []

    @abstractmethod
    async def parse(self, file_path: str, content: str) -> ParsedFile:
        """Parse a single file and return structured data."""
