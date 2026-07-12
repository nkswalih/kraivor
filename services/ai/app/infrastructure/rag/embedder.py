import logging
from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, provider: str | None = None, api_key: str | None = None):
        self.provider = provider or settings.embedding_provider
        self._model = None
        self._client = None
        self.dimension = 384
        if self.provider == "local":
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(settings.embedding_model)
            except Exception as e:
                logger.warning(
                    "Failed to load sentence_transformers, embedding will raise at call time: %s",
                    e,
                )
        elif self.provider == "openai":
            self._client = AsyncOpenAI(api_key=api_key)
            self.dimension = 1536

    async def embed(self, text: str) -> list[float]:
        if self.provider == "local":
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(settings.embedding_model)
            return self._model.encode(text).tolist()
        response = await self._client.embeddings.create(
            model="text-embedding-3-small", input=text
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "local":
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(settings.embedding_model)
            return self._model.encode(texts, batch_size=32).tolist()
        response = await self._client.embeddings.create(
            model="text-embedding-3-small", input=texts
        )
        return [d.embedding for d in response.data]
