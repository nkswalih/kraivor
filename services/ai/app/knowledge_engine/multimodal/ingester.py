"""Unified Multi-Modal Ingester — detect, extract, embed, store.

Orchestrates PDF, image, and audio extraction into a single pipeline.
Automatically detects file type, extracts text, chunks it, generates
embeddings, and stores in the knowledge base.
"""

from __future__ import annotations

import hashlib
import logging
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path

from ..config import KnowledgeEngineConfig
from ..store.knowledge_indexer import KnowledgeIndexer

logger = logging.getLogger(__name__)

# Supported MIME types and their handlers
MIME_TYPE_MAP = {
    # PDF
    "application/pdf": "pdf",
    # Images
    "image/png": "image",
    "image/jpeg": "image",
    "image/gif": "image",
    "image/bmp": "image",
    "image/webp": "image",
    "image/tiff": "image",
    # Audio
    "audio/wav": "audio",
    "audio/mpeg": "audio",
    "audio/mp3": "audio",
    "audio/mp4": "audio",
    "audio/ogg": "audio",
    "audio/flac": "audio",
    "audio/webm": "audio",
}

EXTENSION_MAP = {
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".bmp": "image",
    ".webp": "image",
    ".tiff": "image",
    ".tif": "image",
    ".wav": "audio",
    ".mp3": "audio",
    ".m4a": "audio",
    ".ogg": "audio",
    ".flac": "audio",
    ".webm": "audio",
    ".mp4": "audio",
}


@dataclass
class IngestionResult:
    """Result from multi-modal ingestion."""
    success: bool
    source_type: str  # "pdf", "image", "audio", "text", "url"
    content_type: str
    title: str | None = None
    text: str = ""
    total_characters: int = 0
    chunk_count: int = 0
    knowledge_ids: list[str] = field(default_factory=list)
    language: str | None = None
    metadata: dict = field(default_factory=dict)
    error: str | None = None


class MultiModalIngester:
    """Orchestrates multi-modal content extraction and ingestion."""

    # Max file size: 50MB
    MAX_FILE_SIZE = 50 * 1024 * 1024

    # Max text length for a single ingestion (prevent memory issues)
    MAX_TEXT_LENGTH = 500_000

    def __init__(self, indexer: KnowledgeIndexer | None = None):
        self.config = KnowledgeEngineConfig()
        self.indexer = indexer or KnowledgeIndexer()
        self._pdf_extractor = None
        self._image_ocr = None
        self._audio_transcriber = None

    @property
    def pdf_extractor(self):
        if self._pdf_extractor is None:
            from .pdf_extractor import PDFExtractor
            self._pdf_extractor = PDFExtractor()
        return self._pdf_extractor

    @property
    def image_ocr(self):
        if self._image_ocr is None:
            from .image_ocr import ImageOCR
            self._image_ocr = ImageOCR()
        return self._image_ocr

    @property
    def audio_transcriber(self):
        if self._audio_transcriber is None:
            from .audio_transcriber import AudioTranscriber
            self._audio_transcriber = AudioTranscriber()
        return self._audio_transcriber

    def detect_type(self, filename: str | None = None, mime_type: str | None = None) -> str | None:
        """Detect content type from filename or MIME type."""
        if mime_type and mime_type in MIME_TYPE_MAP:
            return MIME_TYPE_MAP[mime_type]

        if filename:
            ext = Path(filename).suffix.lower()
            if ext in EXTENSION_MAP:
                return EXTENSION_MAP[ext]

            # Try mimetypes fallback
            guessed, _ = mimetypes.guess_type(filename)
            if guessed and guessed in MIME_TYPE_MAP:
                return MIME_TYPE_MAP[guessed]

        return None

    async def ingest_file(
        self,
        file_bytes: bytes,
        filename: str | None = None,
        mime_type: str | None = None,
        workspace_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
        language: str | None = None,
    ) -> IngestionResult:
        """Ingest a file by detecting type and extracting content."""
        # Validate size
        if len(file_bytes) > self.MAX_FILE_SIZE:
            return IngestionResult(
                success=False,
                source_type="unknown",
                content_type=mime_type or "unknown",
                error=f"File too large: {len(file_bytes)} bytes (max: {self.MAX_FILE_SIZE})",
            )

        # Detect type
        content_type = self.detect_type(filename, mime_type)
        if content_type is None:
            return IngestionResult(
                success=False,
                source_type="unknown",
                content_type=mime_type or "unknown",
                error=f"Unsupported file type: {mime_type or filename}",
            )

        logger.info("Ingesting %s file: %s (%d bytes)", content_type, filename, len(file_bytes))

        try:
            if content_type == "pdf":
                return await self._ingest_pdf(file_bytes, filename, workspace_id, user_id, tags, language)
            elif content_type == "image":
                return await self._ingest_image(file_bytes, filename, workspace_id, user_id, tags, language)
            elif content_type == "audio":
                return await self._ingest_audio(file_bytes, filename, workspace_id, user_id, tags, language)
        except Exception as e:
            logger.error("Ingestion failed for %s: %s", filename, e, exc_info=True)
            return IngestionResult(
                success=False,
                source_type=content_type,
                content_type=mime_type or "unknown",
                error=str(e),
            )

    async def ingest_url(
        self,
        url: str,
        workspace_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
    ) -> IngestionResult:
        """Ingest content from a URL. Downloads and detects type."""
        import httpx

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        content_type_header = resp.headers.get("content-type", "")
        filename = url.split("/")[-1].split("?")[0] if "/" in url else None

        return await self.ingest_file(
            file_bytes=resp.content,
            filename=filename,
            mime_type=content_type_header.split(";")[0].strip() if content_type_header else None,
            workspace_id=workspace_id,
            user_id=user_id,
            tags=tags,
        )

    async def ingest_batch(
        self,
        files: list[tuple[bytes, str, str | None]],  # [(bytes, filename, mime_type)]
        workspace_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
    ) -> list[IngestionResult]:
        """Ingest multiple files in sequence."""
        results = []
        for file_bytes, filename, mime_type in files:
            result = await self.ingest_file(
                file_bytes=file_bytes,
                filename=filename,
                mime_type=mime_type,
                workspace_id=workspace_id,
                user_id=user_id,
                tags=tags,
            )
            results.append(result)
        return results

    async def ingest_text(
        self,
        text: str,
        title: str | None = None,
        source_url: str | None = None,
        workspace_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
        language: str | None = None,
    ) -> IngestionResult:
        """Ingest raw text content (for text files, markdown, etc.)."""
        if not text.strip():
            return IngestionResult(
                success=False,
                source_type="text",
                content_type="text/plain",
                error="Empty text content",
            )

        # Generate source URL if not provided
        if not source_url:
            text_hash = hashlib.sha256(text[:1024].encode()).hexdigest()[:16]
            source_url = f"text://{workspace_id}/{text_hash}"

        # Detect language if not provided
        if not language:
            language = self._detect_language(text)

        # Store via indexer
        try:
            knowledge_ids = await self.indexer.index_knowledge(
                workspace_id=workspace_id or "default",
                source_url=source_url,
                source_provider="text",
                source_type="text",
                title=title or source_url,
                content=text,
                trust_score=0.7,
                metadata={
                    "language": language,
                    "user_id": user_id,
                    "ingestion_method": "text",
                },
                language=language,
            )

            return IngestionResult(
                success=True,
                source_type="text",
                content_type="text/plain",
                title=title,
                text=text[:1000],  # preview
                total_characters=len(text),
                chunk_count=len(knowledge_ids),
                knowledge_ids=[knowledge_ids],
                language=language,
            )
        except Exception as e:
            return IngestionResult(
                success=False,
                source_type="text",
                content_type="text/plain",
                error=str(e),
            )

    async def _ingest_pdf(
        self,
        file_bytes: bytes,
        filename: str | None,
        workspace_id: str | None,
        user_id: str | None,
        tags: list[str] | None,
        language: str | None,
    ) -> IngestionResult:
        """Ingest a PDF file."""
        result = await self.pdf_extractor.extract_from_bytes(file_bytes)

        if not result.text.strip():
            return IngestionResult(
                success=False,
                source_type="pdf",
                content_type="application/pdf",
                error="No text content extracted from PDF",
            )

        # Truncate if too long
        text = result.text[:self.MAX_TEXT_LENGTH]

        source_url = f"pdf://{workspace_id}/{filename or 'upload'}"
        title = result.title or filename or "Uploaded PDF"

        knowledge_id = await self.indexer.index_knowledge(
            workspace_id=workspace_id or "default",
            source_url=source_url,
            source_provider="pdf",
            source_type="pdf",
            title=title,
            content=text,
            trust_score=0.6,
            author=result.author,
            metadata={
                "original_filename": filename,
                "page_count": result.page_count,
                "author": result.author,
                "language": language or result.language,
                "user_id": user_id,
                "extraction_metadata": result.metadata,
            },
            original_filename=filename,
            language=language or result.language,
        )

        return IngestionResult(
            success=True,
            source_type="pdf",
            content_type="application/pdf",
            title=title,
            text=text[:500],
            total_characters=len(text),
            chunk_count=1,
            knowledge_ids=[knowledge_id],
            language=language or result.language,
            metadata={
                "page_count": result.page_count,
                "author": result.author,
            },
        )

    async def _ingest_image(
        self,
        file_bytes: bytes,
        filename: str | None,
        workspace_id: str | None,
        user_id: str | None,
        tags: list[str] | None,
        language: str | None,
    ) -> IngestionResult:
        """Ingest an image via OCR."""
        result = await self.image_ocr.extract_from_bytes(file_bytes)

        if not result.text.strip():
            return IngestionResult(
                success=False,
                source_type="image",
                content_type="image",
                error="No text detected in image",
            )

        text = result.text[:self.MAX_TEXT_LENGTH]
        source_url = f"image://{workspace_id}/{filename or 'upload'}"
        title = filename or "Uploaded Image"

        knowledge_id = await self.indexer.index_knowledge(
            workspace_id=workspace_id or "default",
            source_url=source_url,
            source_provider="image",
            source_type="image",
            title=title,
            content=text,
            trust_score=0.5,
            metadata={
                "original_filename": filename,
                "ocr_confidence": result.confidence,
                "words_detected": len(result.bounding_boxes),
                "language": language or result.language,
                "user_id": user_id,
            },
            original_filename=filename,
            language=language or result.language,
        )

        return IngestionResult(
            success=True,
            source_type="image",
            content_type="image",
            title=title,
            text=text[:500],
            total_characters=len(text),
            chunk_count=1,
            knowledge_ids=[knowledge_id],
            language=language or result.language,
            metadata={
                "ocr_confidence": result.confidence,
                "words_detected": len(result.bounding_boxes),
            },
        )

    async def _ingest_audio(
        self,
        file_bytes: bytes,
        filename: str | None,
        workspace_id: str | None,
        user_id: str | None,
        tags: list[str] | None,
        language: str | None,
    ) -> IngestionResult:
        """Ingest audio via transcription."""
        result = await self.audio_transcriber.transcribe_from_bytes(file_bytes)

        if not result.text.strip():
            return IngestionResult(
                success=False,
                source_type="audio",
                content_type="audio",
                error="No speech detected in audio",
            )

        text = result.text[:self.MAX_TEXT_LENGTH]
        source_url = f"audio://{workspace_id}/{filename or 'upload'}"
        title = filename or "Uploaded Audio"

        knowledge_id = await self.indexer.index_knowledge(
            workspace_id=workspace_id or "default",
            source_url=source_url,
            source_provider="audio",
            source_type="audio",
            title=title,
            content=text,
            trust_score=0.5,
            metadata={
                "original_filename": filename,
                "duration_seconds": result.duration_seconds,
                "segment_count": len(result.segments),
                "language": language or result.language,
                "language_probability": result.language_probability,
                "user_id": user_id,
            },
            original_filename=filename,
            language=language or result.language,
        )

        return IngestionResult(
            success=True,
            source_type="audio",
            content_type="audio",
            title=title,
            text=text[:500],
            total_characters=len(text),
            chunk_count=1,
            knowledge_ids=[knowledge_id],
            language=language or result.language,
            metadata={
                "duration_seconds": result.duration_seconds,
                "segment_count": len(result.segments),
            },
        )

    def _detect_language(self, text: str) -> str | None:
        """Detect language of text using langdetect."""
        try:
            from langdetect import detect
            return detect(text[:1000])
        except Exception:
            return "en"  # fallback

    def get_supported_types(self) -> dict[str, list[str]]:
        """Return all supported content types and their extensions."""
        return {
            "pdf": [".pdf"],
            "image": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"],
            "audio": [".wav", ".mp3", ".m4a", ".ogg", ".flac", ".webm", ".mp4"],
        }
