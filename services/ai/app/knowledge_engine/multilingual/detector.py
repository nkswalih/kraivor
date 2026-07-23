"""Language Detector — identifies text language using langdetect.

Provides fast, local language detection without API keys.
Supports 55+ languages with confidence scores.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Common language codes to human-readable names
LANGUAGE_NAMES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)", "ja": "Japanese", "ko": "Korean",
    "ar": "Arabic", "hi": "Hindi", "bn": "Bengali", "pa": "Punjabi",
    "tr": "Turkish", "vi": "Vietnamese", "th": "Thai", "pl": "Polish",
    "nl": "Dutch", "sv": "Swedish", "da": "Danish", "fi": "Finnish",
    "no": "Norwegian", "cs": "Czech", "sk": "Slovak", "hu": "Hungarian",
    "ro": "Romanian", "bg": "Bulgarian", "hr": "Croatian", "sl": "Slovenian",
    "uk": "Ukrainian", "el": "Greek", "he": "Hebrew", "fa": "Persian",
    "ur": "Urdu", "ms": "Malay", "id": "Indonesian", "tl": "Filipino",
    "sw": "Swahili", "ta": "Tamil", "te": "Telugu", "mr": "Marathi",
    "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam", "my": "Myanmar",
    "km": "Khmer", "si": "Sinhala", "ne": "Nepali", "am": "Amharic",
    "yo": "Yoruba", "zu": "Zulu", "af": "Afrikaans", "sq": "Albanian",
    "et": "Estonian", "lv": "Latvian", "lt": "Lithuanian",
}


@dataclass
class DetectionResult:
    """Result from language detection."""
    language: str
    language_name: str
    confidence: float
    all_detections: list[dict] | None = None


class LanguageDetector:
    """Detects text language using langdetect."""

    def __init__(self):
        self._available = None

    def _check_available(self) -> bool:
        if self._available is None:
            try:
                import langdetect
                self._available = True
            except ImportError:
                self._available = False
        return self._available

    def detect(self, text: str) -> DetectionResult:
        """Detect the language of a text string."""
        if not self._check_available():
            return DetectionResult(
                language="en",
                language_name="English",
                confidence=0.0,
            )

        from langdetect import detect, detect_langs, LangDetectException

        try:
            lang = detect(text[:2000])
        except LangDetectException:
            return DetectionResult(
                language="unknown",
                language_name="Unknown",
                confidence=0.0,
            )

        # Get all detection probabilities
        try:
            probs = detect_langs(text[:2000])
            all_detections = [
                {"language": str(p.lang), "probability": round(p.prob, 3)}
                for p in probs
            ]
        except LangDetectException:
            all_detections = []

        # Find confidence for top language
        confidence = 0.0
        for d in all_detections:
            if d["language"] == lang:
                confidence = d["probability"]
                break

        lang_name = LANGUAGE_NAMES.get(lang, lang)

        return DetectionResult(
            language=lang,
            language_name=lang_name,
            confidence=confidence,
            all_detections=all_detections,
        )

    def detect_batch(self, texts: list[str]) -> list[DetectionResult]:
        """Detect languages for multiple texts."""
        return [self.detect(text) for text in texts]

    def get_supported_languages(self) -> dict[str, str]:
        """Return all supported language codes and names."""
        return LANGUAGE_NAMES.copy()
