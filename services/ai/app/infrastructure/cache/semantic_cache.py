import json
import time
from app.infrastructure.cache.redis_client import get_redis
from app.monitoring.metrics import cache_hits, cache_misses


class SemanticCache:
    def __init__(self, ttl: int = 3600, similarity_threshold: float = 0.95):
        self.ttl = ttl
        self.similarity_threshold = similarity_threshold

    async def get(self, key: str) -> str | None:
        r = await get_redis()
        cached = await r.get(f"semantic:{key}")
        if cached:
            cache_hits.labels("semantic").inc()
            return cached
        cache_misses.labels("semantic").inc()
        return None

    async def set(self, key: str, value: str) -> None:
        r = await get_redis()
        await r.setex(f"semantic:{key}", self.ttl, value)

    async def get_or_compute(self, key: str, compute_fn, ttl: int | None = None) -> str:
        cached = await self.get(key)
        if cached:
            return cached
        value = await compute_fn()
        await self.set(key, value)
        if ttl:
            r = await get_redis()
            await r.expire(f"semantic:{key}", ttl)
        return value
