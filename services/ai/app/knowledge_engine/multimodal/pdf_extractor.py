"""PDF Extractor — extracts text, tables, and metadata from PDF documents.

Uses PyMuPDF (fitz) for fast, local PDF text extraction. No API keys needed.
Handles:
- Multi-page documents
- Text with embedded formatting
- Table extraction (basic)
- Metadata extraction (title, author, dates)
- Page-by-page chunking for large documents
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PDFExtractionResult:
    """Result from PDF text extraction."""
    text: str
    title: str | None = None
    author: str | None = None
    page_count: int = 0
    metadata: dict = field(default_factory=dict)
    page_texts: list[dict] = field(default_factory=list)  # [{page, text, char_count}]
    total_characters: int = 0
    language: str | None = None


class PDFExtractor:
    """Extracts text content from PDF files using PyMuPDF."""

    MAX_PAGE_TEXT_LENGTH = 50000  # safety limit per page

    async def extract_from_bytes(self, pdf_bytes: bytes) -> PDFExtractionResult:
        """Extract text from raw PDF bytes."""
        try:
            import pymupdf
        except ImportError:
            raise RuntimeError(
                "pymupdf is not installed. Install with: pip install pymupdf"
            )

        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise ValueError(f"Invalid PDF file: {e}")

        return self._extract_doc(doc)

    async def extract_from_path(self, file_path: str) -> PDFExtractionResult:
        """Extract text from a PDF file path."""
        try:
            import pymupdf
        except ImportError:
            raise RuntimeError(
                "pymupdf is not installed. Install with: pip install pymupdf"
            )

        try:
            doc = pymupdf.open(file_path)
        except Exception as e:
            raise ValueError(f"Cannot open PDF at {file_path}: {e}")

        return self._extract_doc(doc)

    def _extract_doc(self, doc) -> PDFExtractionResult:
        """Extract content from an opened PyMuPDF document."""
        metadata = doc.metadata or {}
        title = metadata.get("title") or metadata.get("subject") or None
        author = metadata.get("author") or None

        page_texts = []
        all_text_parts = []

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)

            # Extract text with block sorting for natural reading order
            blocks = page.get_text("blocks")
            # Sort by vertical position, then horizontal
            blocks.sort(key=lambda b: (round(b[1] / 10) * 10, b[0]))

            page_text_parts = []
            for block in blocks:
                if block[6] == 0:  # text block (type 0)
                    text = block[4].strip()
                    if text:
                        page_text_parts.append(text)

            page_text = "\n\n".join(page_text_parts)

            # Safety limit
            if len(page_text) > self.MAX_PAGE_TEXT_LENGTH:
                page_text = page_text[: self.MAX_PAGE_TEXT_LENGTH] + "\n[truncated]"

            if page_text.strip():
                page_texts.append({
                    "page": page_num + 1,
                    "text": page_text,
                    "char_count": len(page_text),
                })
                all_text_parts.append(page_text)

        full_text = "\n\n---\n\n".join(all_text_parts)

        # Extract tables if present
        tables_text = self._extract_tables(doc)
        if tables_text:
            full_text += f"\n\n## Tables\n\n{tables_text}"

        doc.close()

        result = PDFExtractionResult(
            text=full_text,
            title=title,
            author=author,
            page_count=len(doc) if hasattr(doc, '__len__') else len(page_texts),
            metadata={
                "format": metadata.get("format", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "encryption": metadata.get("encryption", ""),
            },
            page_texts=page_texts,
            total_characters=len(full_text),
        )

        logger.info(
            "PDF extracted: %d pages, %d characters",
            result.page_count, result.total_characters,
        )
        return result

    def _extract_tables(self, doc) -> str:
        """Extract tables from PDF pages."""
        tables_text = []

        try:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                tab_finder = page.find_tables()

                if tab_finder and tab_finder.tables:
                    for table in tab_finder.tables:
                        try:
                            data = table.extract()
                            if data:
                                # Convert to markdown table
                                header = data[0] if data else []
                                rows = data[1:] if len(data) > 1 else []

                                lines = []
                                lines.append("| " + " | ".join(str(c or "") for c in header) + " |")
                                lines.append("| " + " | ".join("---" for _ in header) + " |")
                                for row in rows:
                                    lines.append("| " + " | ".join(str(c or "") for c in row) + " |")

                                tables_text.append("\n".join(lines))
                        except Exception:
                            continue
        except Exception as e:
            logger.debug("Table extraction failed: %s", e)

        return "\n\n".join(tables_text) if tables_text else ""

    def get_supported_formats(self) -> list[str]:
        """Return supported file extensions."""
        return [".pdf"]
