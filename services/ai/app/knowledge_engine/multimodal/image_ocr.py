"""Image OCR — extracts text from images using EasyOCR.

Uses EasyOCR for local, free optical character recognition. No API keys needed.
Handles:
- Screenshots, diagrams, charts
- Handwritten text (limited)
- Multi-language text in images
- Returns text with confidence scores
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result from image OCR extraction."""
    text: str
    confidence: float = 0.0
    language: str | None = None
    bounding_boxes: list[dict] = field(default_factory=list)
    total_characters: int = 0
    metadata: dict = field(default_factory=dict)


class ImageOCR:
    """Extracts text from images using EasyOCR."""

    # Languages to detect by default
    DEFAULT_LANGUAGES = ["en"]

    def __init__(self, languages: list[str] | None = None):
        self.languages = languages or self.DEFAULT_LANGUAGES
        self._reader = None

    def _get_reader(self):
        """Lazy-load the EasyOCR reader."""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(self.languages, gpu=False)
            except ImportError:
                raise RuntimeError(
                    "easyocr is not installed. Install with: pip install easyocr"
                ) from None
        return self._reader

    async def extract_from_bytes(
        self,
        image_bytes: bytes,
        languages: list[str] | None = None,
    ) -> OCRResult:
        """Extract text from raw image bytes."""
        import numpy as np
        from PIL import Image

        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            image_array = np.array(image)
        except Exception as e:
            raise ValueError(f"Invalid image file: {e}") from e

        return await self._extract_from_array(image_array, languages)

    async def extract_from_path(
        self,
        file_path: str,
        languages: list[str] | None = None,
    ) -> OCRResult:
        """Extract text from an image file path."""
        import numpy as np
        from PIL import Image

        try:
            image = Image.open(file_path)
            if image.mode != "RGB":
                image = image.convert("RGB")
            image_array = np.array(image)
        except Exception as e:
            raise ValueError(f"Cannot open image at {file_path}: {e}") from e

        return await self._extract_from_array(image_array, languages)

    async def _extract_from_array(
        self,
        image_array,
        languages: list[str] | None = None,
    ) -> OCRResult:
        """Extract text from a numpy array image."""
        reader = self._get_reader()

        try:
            # EasyOCR readtext returns list of (bbox, text, confidence)
            results = reader.readtext(image_array)
        except Exception as e:
            logger.warning("OCR extraction failed: %s", e)
            return OCRResult(text="", confidence=0.0)

        if not results:
            return OCRResult(text="", confidence=0.0)

        # Build results
        bounding_boxes = []
        text_parts = []
        confidences = []

        for bbox, text, confidence in results:
            text_parts.append(text)
            confidences.append(confidence)
            bounding_boxes.append({
                "text": text,
                "confidence": round(confidence, 3),
                "bbox": bbox,  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            })

        full_text = " ".join(text_parts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        result = OCRResult(
            text=full_text,
            confidence=round(avg_confidence, 3),
            language=self.languages[0] if self.languages else None,
            bounding_boxes=bounding_boxes,
            total_characters=len(full_text),
            metadata={
                "words_detected": len(results),
                "languages_used": self.languages,
            },
        )

        logger.info(
            "OCR extracted: %d words, %.1f%% confidence",
            len(results), avg_confidence * 100,
        )
        return result

    async def extract_from_url(self, url: str) -> OCRResult:
        """Download an image from URL and extract text."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "image" not in content_type and not url.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")):
            raise ValueError(f"URL does not point to an image: {content_type}")

        return await self.extract_from_bytes(resp.content)

    def get_supported_formats(self) -> list[str]:
        """Return supported file extensions."""
        return [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff"]
