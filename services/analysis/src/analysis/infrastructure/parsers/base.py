from app.core.logging import get_logger
from app.domain.contracts.parser import AbstractParser, ParsedFile

logger = get_logger(__name__)


class ChainedParser:
    """Multi-language parser that delegates to language-specific parsers.

    Tries parsers in order of language match. Falls back to
    simpler parsing if a specialized parser is unavailable.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, AbstractParser] = {}
        self._fallback_parser: AbstractParser | None = None

    def register(self, parser: AbstractParser) -> None:
        """Register a language-specific parser."""
        for ext in parser.supported_extensions:
            self._parsers[ext] = parser

    def set_fallback(self, parser: AbstractParser) -> None:
        """Set a fallback parser for unsupported languages."""
        self._fallback_parser = parser

    def get_parser(self, file_path: str) -> AbstractParser | None:
        """Get the appropriate parser for a file based on extension."""
        import os

        ext = os.path.splitext(file_path)[1].lower()
        if ext in self._parsers:
            return self._parsers[ext]

        # Also check by filename (e.g., Dockerfile)
        filename = os.path.basename(file_path)
        for parser in self._parsers.values():
            if filename in parser.supported_extensions:
                return parser

        return self._fallback_parser

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        """Parse a file using the best available parser."""
        parser = self.get_parser(file_path)
        if parser is None:
            return ParsedFile(
                path=file_path,
                language="unknown",
                content=content,
                size_bytes=len(content.encode("utf-8")),
                lines_count=content.count("\n") + 1,
            )
        return await parser.parse(file_path, content)
