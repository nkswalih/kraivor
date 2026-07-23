import logging
import time

from fastapi import HTTPException, Request

from app.core.config import settings
from app.infrastructure.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

LUA_SLIDING_WINDOW = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, now .. ':' .. math.random())
    redis.call('EXPIRE', key, window)
    return {1, count + 1, limit}
else
    return {0, count, limit}
end
"""


async def check_rate_limit(request: Request) -> None:
    user_id = getattr(request.state, "user_id", "anonymous")
    key = f"ratelimit:ai:{user_id}"
    now = time.time()
    window = 60
    limit = 60

    if settings.redis__url:
        try:
            r = await get_redis()
            allowed, count, max_limit = await r.eval(
                LUA_SLIDING_WINDOW, 1, key, now, window, limit
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. {count}/{max_limit} requests used.",
                        "retry_after": window,
                    },
                )
        except HTTPException:
            raise
        except Exception:
            logger.warning("rate_limiter_check_failed", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "rate_limiter_unavailable",
                    "message": "Rate limiting service unavailable. Please try again later.",
                },
            )
