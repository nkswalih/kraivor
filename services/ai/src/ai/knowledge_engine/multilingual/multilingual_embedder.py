"""Multilingual Embedder — generates language-agnostic embeddings.

Uses sentence-transformers with multilingual models for cross-lingual
semantic search. Supports 50+ languages with a single model.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MultilingualEmbeddingResult:
    """Result from multilingual embedding."""
    embedding: list[float]
    dimension: int
    model: str
    text_length: int


class MultilingualEmbedder:
    """Generates multilingual embeddings using sentence-transformers.

    Uses paraphrase-multilingual-MiniLM-L12-v2 by default:
    - 384-dimensional embeddings
    - Supports 50+ languages
    - Optimized for cross-lingual similarity
    """

    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    FALLBACK_MODEL = "paraphrase-multilingual-mpnet-base-v2"

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None

    def _get_model(self):
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers is not installed. "
                    "Install with: pip install sentence-transformers"
                ) from None
        return self._model

    def embed(self, text: str) -> MultilingualEmbeddingResult:
        """Generate a multilingual embedding for text."""
        model = self._get_model()

        try:
            embedding = model.encode(text, normalize_embeddings=True)
            embedding_list = embedding.tolist()
        except Exception as e:
            logger.warning("Multilingual embedding failed: %s", e)
            # Return zero vector as fallback
            embedding_list = [0.0] * 384

        return MultilingualEmbeddingResult(
            embedding=embedding_list,
            dimension=len(embedding_list),
            model=self.model_name,
            text_length=len(text),
        )

    def embed_batch(self, texts: list[str]) -> list[MultilingualEmbeddingResult]:
        """Generate embeddings for multiple texts."""
        model = self._get_model()

        try:
            embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
        except Exception as e:
            logger.warning("Batch embedding failed: %s", e)
            return [
                MultilingualEmbeddingResult(
                    embedding=[0.0] * 384,
                    dimension=384,
                    model=self.model_name,
                    text_length=len(t),
                )
                for t in texts
            ]

        results = []
        for text, emb in zip(texts, embeddings, strict=False):
            results.append(MultilingualEmbeddingResult(
                embedding=emb.tolist(),
                dimension=len(emb),
                model=self.model_name,
                text_length=len(text),
            ))

        return results

    def get_dimension(self) -> int:
        """Return the embedding dimension."""
        model = self._get_model()
        return model.get_sentence_embedding_dimension()

    def get_model_info(self) -> dict:
        """Return information about the current model."""
        return {
            "model": self.model_name,
            "dimension": self.get_dimension() if self._model else 384,
            "languages": "50+",
        }
