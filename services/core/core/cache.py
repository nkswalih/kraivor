import json
from typing import Any

import functools
import hashlib
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_SENTINEL = object()


def _make_key(prefix: str, *args, **kwargs) -> str:
    raw = f"{prefix}:{hashlib.md5(json.dumps([args, kwargs], sort_keys=True, default=str).encode(), usedforsecurity=False).hexdigest()}"
    return raw


def cached(prefix: str, timeout: int | None = None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ttl = (
                timeout
                if timeout is not None
                else getattr(settings, "DEFAULT_CACHE_TTL", 300)
            )
            key = _make_key(prefix, *args, **kwargs)
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        return wrapper

    return decorator


def invalidate_cache(prefix: str, *args, **kwargs):
    key = _make_key(prefix, *args, **kwargs)
    cache.delete(key)


def invalidate_pattern(pattern: str):
    try:
        from django_redis import get_redis_connection

        conn = get_redis_connection("default")
        full_pattern = f"{settings.CACHES['default']['KEY_PREFIX']}:{pattern}*"
        cursor = 0
        keys: list[str] = []
        while True:
            cursor, batch = conn.scan(cursor=cursor, match=full_pattern, count=100)
            keys.extend(batch)
            if cursor == 0:
                break
        if keys:
            conn.delete(*keys)
            logger.info(
                "cache.invalidated", extra={"pattern": pattern, "count": len(keys)}
            )
    except Exception:
        logger.exception("cache.invalidate_failed", extra={"pattern": pattern})


class CacheService:
    @staticmethod
    def get_or_set(key: str, timeout: int, fallback: callable) -> Any:
        result = cache.get(key, default=_SENTINEL)
        if result is not _SENTINEL:
            return result
        result = fallback()
        cache.set(key, result, timeout)
        return result

    @staticmethod
    def delete(key: str):
        cache.delete(key)

    @staticmethod
    def touch(key: str, timeout: int) -> bool:
        return cache.touch(key, timeout)
