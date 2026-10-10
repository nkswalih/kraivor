"""Semantic Query Cache — caches LLM responses using embedding similarity.

When a new query comes in, we embed it and search for semantically similar
cached queries. If the cosine similarity exceeds the threshold, we reuse
the cached response instead of calling the LLM again.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time

from app.infrastructure.cache.redis_client import get_redis
from app.monitoring.metrics import cache_hits, cache_misses

logger = logging.getLogger(__name__)

# Redis keys
INDEX_KEY = "semantic_query_cache:entries"  # sorted set: score=timestamp, member=hash
ENTRY_PREFIX = "semantic_query_cache:entry:"  # hash:{query_hash} → {embedding, response, ...}


class SemanticQueryCache:
    """Embedding-similarity query cache backed by Redis.

    Unlike the key-value SemanticCache, this stores query embeddings and
    performs cosine similarity search to find semantically close matches.
    """

    def __init__(
        self,
        ttl: int = 1800,
        similarity_threshold: float = 0.90,
        max_entries: int = 5000,
    ):
        self.ttl = ttl
        self.similarity_threshold = similarity_threshold
        self.max_entries = max_entries
        self._embedder = None  # lazy init to avoid model download at import

    def _get_embedder(self):
        if self._embedder is None:
            from app.infrastructure.rag.embedder import Embedder
            self._embedder = Embedder()
        return self._embedder

    def _hash_key(self, query: str, model: str) -> str:
        return hashlib.sha256(f"{model}::{query.strip().lower()}".encode()).hexdigest()[:16]

    async def get(self, query: str, model: str = "") -> str | None:
        """Find a semantically similar cached response."""
        try:
            r = await get_redis()
            query_embedding = await self._get_embedder().embed(query)

            # Scan recent entries for similarity
            now = time.time()
            entries = await r.zrevrangebyscore(
                INDEX_KEY,
                min=now - self.ttl,
                max="+inf",
                start=0,
                num=min(self.max_entries, 200),
            )

            best_score = -1.0
            best_response = None

            for entry_hash in entries:
                entry_key = f"{ENTRY_PREFIX}{entry_hash.decode()}"
                entry = await r.hgetall(entry_key)
                if not entry:
                    continue

                cached_embedding = json.loads(entry.get(b"embedding", b"[]"))
                if not cached_embedding:
                    continue

                # Cosine similarity (embeddings are normalized)
                score = self._cosine_similarity(query_embedding, cached_embedding)
                if score > best_score:
                    best_score = score
                    best_response = entry.get(b"response", b"").decode()

            if best_score >= self.similarity_threshold and best_response:
                cache_hits.labels("semantic_query").inc()
                logger.info(
                    "query_cache: hit (similarity=%.3f, threshold=%.2f)",
                    best_score,
                    self.similarity_threshold,
                )
                return best_response

            cache_misses.labels("semantic_query").inc()
            return None

        except Exception as e:
            logger.debug("query_cache.get failed: %s", e)
            cache_misses.labels("semantic_query").inc()
            return None

    async def set(self, query: str, model: str, response: str) -> None:
        """Store a query→response with its embedding."""
        try:
            r = await get_redis()
            query_embedding = await self._get_embedder().embed(query)
            entry_hash = self._hash_key(query, model)

            entry_key = f"{ENTRY_PREFIX}{entry_hash}"
            now = time.time()

            # Store entry
            await r.hset(
                entry_key,
                mapping={
                    "embedding": json.dumps(query_embedding),
                    "response": response,
                    "model": model,
                    "created_at": str(now),
                    "query": query[:500],
                },
            )
            await r.expire(entry_key, self.ttl)

            # Add to sorted set for time-based lookup
            await r.zadd(INDEX_KEY, {entry_hash: now})

            # Trim old entries
            trim_count = await r.zcard(INDEX_KEY)
            if trim_count > self.max_entries:
                await r.zremrangebyrank(INDEX_KEY, 0, trim_count - self.max_entries - 1)

        except Exception as e:
            logger.debug("query_cache.set failed: %s", e)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
