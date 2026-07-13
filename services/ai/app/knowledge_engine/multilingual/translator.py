"""Language Translator — translates text between languages using argostranslate.

Uses argostranslate for free, offline machine translation. No API keys needed.
Supports 20+ languages with decent quality.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """Result from language translation."""
    translated_text: str
    source_language: str
    target_language: str
    original_length: int
    translated_length: int
    success: bool = True
    error: str | None = None


class LanguageTranslator:
    """Translates text between languages using argostranslate."""

    # Language pairs that argostranslate supports well
    SUPPORTED_PAIRS = {
        ("en", "es"), ("en", "fr"), ("en", "de"), ("en", "it"), ("en", "pt"),
        ("en", "ru"), ("en", "zh"), ("en", "ja"), ("en", "ko"), ("en", "ar"),
        ("en", "hi"), ("en", "nl"), ("en", "pl"), ("en", "tr"), ("en", "vi"),
        ("es", "fr"), ("es", "de"), ("fr", "de"), ("fr", "it"), ("de", "it"),
    }

    def __init__(self):
        self._installed = False

    def _ensure_installed(self):
        """Install language packages if not already done."""
        if self._installed:
            return

        try:
            import argostranslate.package
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()

            # Install packages for common language pairs
            installed = set()
            for pkg in available_packages:
                if pkg.code in installed:
                    continue
                try:
                    pkg.install()
                    installed.add(pkg.code)
                except Exception:
                    continue

            self._installed = True
        except ImportError:
            logger.warning("argostranslate not installed. Translation unavailable.")
        except Exception as e:
            logger.warning("Failed to install translation packages: %s", e)

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str | None = None,
    ) -> TranslationResult:
        """Translate text to the target language."""
        if not text.strip():
            return TranslationResult(
                translated_text="",
                source_language=source_language or "unknown",
                target_language=target_language,
                original_length=0,
                translated_length=0,
                success=False,
                error="Empty text",
            )

        # Auto-detect source language if not provided
        if not source_language:
            from .detector import LanguageDetector
            detector = LanguageDetector()
            detection = detector.detect(text)
            source_language = detection.language

        # Same language — no translation needed
        if source_language == target_language:
            return TranslationResult(
                translated_text=text,
                source_language=source_language,
                target_language=target_language,
                original_length=len(text),
                translated_length=len(text),
            )

        try:
            import argostranslate.translate
        except ImportError:
            return TranslationResult(
                translated_text=text,
                source_language=source_language,
                target_language=target_language,
                original_length=len(text),
                translated_length=len(text),
                success=False,
                error="argostranslate not installed",
            )

        self._ensure_installed()

        try:
            # Map common codes
            src = self._normalize_code(source_language)
            tgt = self._normalize_code(target_language)

            translated = argostranslate.translate.translate(text, src, tgt)

            return TranslationResult(
                translated_text=translated,
                source_language=source_language,
                target_language=target_language,
                original_length=len(text),
                translated_length=len(translated),
            )
        except Exception as e:
            logger.warning("Translation failed: %s", e)
            return TranslationResult(
                translated_text=text,
                source_language=source_language,
                target_language=target_language,
                original_length=len(text),
                translated_length=len(text),
                success=False,
                error=str(e),
            )

    def translate_to_english(self, text: str, source_language: str | None = None) -> TranslationResult:
        """Translate text to English (most common use case)."""
        return self.translate(text, "en", source_language)

    def _normalize_code(self, code: str) -> str:
        """Normalize language codes for argostranslate."""
        mapping = {
            "zh-cn": "zh", "zh-tw": "zh", "zh": "zh",
            "pt-br": "pt", "pt-pt": "pt",
            "en-us": "en", "en-gb": "en",
        }
        return mapping.get(code.lower(), code.lower())

    def get_supported_languages(self) -> list[str]:
        """Return list of supported language codes."""
        langs = set()
        for src, tgt in self.SUPPORTED_PAIRS:
            langs.add(src)
            langs.add(tgt)
        return sorted(langs)
