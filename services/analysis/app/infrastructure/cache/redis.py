from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings


settings = get_settings()
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisCache:
    """Redis cache adapter for distributed caching.

    Used for:
    - Celery result backend
    - Rate limiting counters
    - Temporary job state
    - Pub/sub event distribution
    """

    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._client = aioredis.from_url(
                str(settings.redis.url),
                socket_timeout=settings.redis.socket_timeout,
                retry_on_timeout=settings.redis.retry_on_timeout,
                decode_responses=True,
            )
            await self._client.ping()
            logger.info("redis_connected")
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("redis_disconnected")

    async def get(self, key: str) -> str | None:
        if self._client is None:
            return None
        return await self._client.get(key)

    async def set(
        self, key: str, value: str, ttl: int | None = None
    ) -> None:
        if self._client is None:
            return
        if ttl:
            await self._client.setex(key, ttl, value)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> None:
        if self._client is None:
            return
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        if self._client is None:
            return False
        return await self._client.exists(key) > 0

    async def incr(self, key: str) -> int:
        if self._client is None:
            return 0
        return await self._client.incr(key)

    async def expire(self, key: str, ttl: int) -> bool:
        if self._client is None:
            return False
        return await self._client.expire(key, ttl)

    async def publish(self, channel: str, message: str) -> int:
        if self._client is None:
            return 0
        return await self._client.publish(channel, message)

    async def lpush(self, key: str, *values: str) -> int:
        if self._client is None:
            return 0
        return await self._client.lpush(key, *values)

    async def lrange(
        self, key: str, start: int = 0, end: int = -1
    ) -> list[str]:
        if self._client is None:
            return []
        return await self._client.lrange(key, start, end)

    @property
    def client(self) -> aioredis.Redis | None:
        return self._client
