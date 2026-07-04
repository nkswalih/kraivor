import time

from fastapi import HTTPException, Request

from app.core.config import settings

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
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis__url, decode_responses=True)
            allowed, count, max_limit = await r.eval(LUA_SLIDING_WINDOW, 1, key, now, window, limit)
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. {count}/{max_limit} requests used.",
                        "retry_after": window,
                    },
                )
        except ImportError:
            pass
        except Exception:
            pass
