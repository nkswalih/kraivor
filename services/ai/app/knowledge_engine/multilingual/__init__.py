"""Multi-Language Support — detect, translate, and embed across languages."""

from .detector import LanguageDetector
from .translator import LanguageTranslator
from .multilingual_embedder import MultilingualEmbedder

__all__ = [
    "LanguageDetector",
    "LanguageTranslator",
    "MultilingualEmbedder",
]
