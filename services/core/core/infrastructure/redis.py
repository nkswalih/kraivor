"""
Redis client singleton for the Core Service.

Provides a shared Redis connection used for:
  - Celery broker (configured via CELERY_BROKER_URL)
  - Notification feed operations (used by apps/notifications/)
  - Presence tracking (used by apps/chat/consumers.py)
  - General caching

Usage:
    from core.infrastructure.redis import get_redis
    r = get_redis()
    r.lpush("notif:feed:user_123", "notif_id")
"""

import logging
from django.conf import settings
from redis import Redis

logger = logging.getLogger(__name__)

_redis: Redis | None = None


def get_redis() -> Redis | None:
    global _redis
    if _redis is None:
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        if not redis_url:
            logger.warning("redis.disabled", extra={"reason": "REDIS_URL not set"})
            return None
        try:
            _redis = Redis.from_url(redis_url, decode_responses=True)
            _redis.ping()
            logger.info("redis.connected", extra={"url": redis_url})
        except Exception as exc:
            logger.error("redis.connection_failed", extra={"error": str(exc)})
            return None
    return _redis
