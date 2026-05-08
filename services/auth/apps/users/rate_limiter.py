"""
Redis-based distributed rate limiter.

Designed to be:
  - Shared across service instances (not in-process memory)
  - Reusable for login throttling, API keys, password reset, etc.
  - Migrated to a dedicated rate-limit service later if needed

Usage:
    limiter = RedisRateLimiter()
    allowed, remaining, retry_after = limiter.check(
        key="resend_verification:user@example.com",
        limit=3,
        window_seconds=3600,   # 1 hour
    )
"""

from __future__ import annotations

import redis
from django.conf import settings


class RateLimitExceeded(Exception):
    """Raised when a rate limit is exceeded."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s.")


class RedisRateLimiter:
    """
    Sliding-window counter rate limiter backed by Redis.

    Uses INCR + EXPIRE in a pipeline to guarantee atomicity for the common
    case.  The window resets fully after `window_seconds` regardless of when
    individual requests were made (fixed-window semantics), which is
    intentional — simpler and predictable enough for email operations.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        url = redis_url or settings.REDIS_URL
        self.client: redis.Redis = redis.from_url(url, decode_responses=True)

    def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int, int]:
        """
        Atomically increment the counter for *key* and check against *limit*.

        Returns:
            (allowed, remaining, retry_after_seconds)

            allowed        — True if the request should proceed
            remaining      — requests remaining in the current window
            retry_after    — seconds until the window resets (0 if allowed)
        """
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        pipe.ttl(key)
        count, _, ttl = pipe.execute()

        allowed = count <= limit
        remaining = max(0, limit - count)
        retry_after = ttl if not allowed else 0
        return allowed, remaining, retry_after

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """Convenience wrapper — returns True if allowed, raises RateLimitExceeded otherwise."""
        allowed, _, retry_after = self.check(key, limit, window_seconds)
        if not allowed:
            raise RateLimitExceeded(retry_after=retry_after)
        return True


# ---------------------------------------------------------------------------
# Module-level singleton — lazy so Redis is NOT connected at import time.
# This allows tests to mock `users.views.rate_limiter` without needing Redis.
# ---------------------------------------------------------------------------

_rate_limiter: "RedisRateLimiter | None" = None


def _get_rate_limiter() -> "RedisRateLimiter":
    global _rate_limiter  # noqa: PLW0603
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter()
    return _rate_limiter


class _LazyRateLimiter:
    """Proxy that defers Redis connection until first use."""

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        return _get_rate_limiter().check(key, limit, window_seconds)

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        return _get_rate_limiter().is_allowed(key, limit, window_seconds)


rate_limiter = _LazyRateLimiter()
