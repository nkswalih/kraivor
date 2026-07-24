"""Redis-backed daily token usage tracker.

Keys:
    usage:daily:{user_id}:{YYYY-MM-DD}:input   -> int (input tokens)
    usage:daily:{user_id}:{YYYY-MM-DD}:output  -> int (output tokens)
    TTL: 48 hours (auto-cleanup)
"""

import logging
from datetime import datetime, timedelta, UTC

from app.core.config import settings
from app.infrastructure.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

_TTL_SECONDS = 48 * 60 * 60  # 48 hours


def _today_key(user_id: str, suffix: str) -> str:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"usage:daily:{user_id}:{today}:{suffix}"


async def increment_daily_usage(
    user_id: str, input_tokens: int = 0, output_tokens: int = 0
) -> dict:
    """Increment the user's daily token counters. Returns current totals."""
    try:
        r = await get_redis()
        input_key = _today_key(user_id, "input")
        output_key = _today_key(user_id, "output")

        pipe = r.pipeline()
        if input_tokens > 0:
            pipe.incrby(input_key, input_tokens)
            pipe.expire(input_key, _TTL_SECONDS)
        if output_tokens > 0:
            pipe.incrby(output_key, output_tokens)
            pipe.expire(output_key, _TTL_SECONDS)
        results = await pipe.execute()

        input_total = int(results[0]) if input_tokens > 0 else int(await r.get(input_key) or 0)
        output_total = int(results[1]) if output_tokens > 0 else int(await r.get(output_key) or 0)

        return {
            "input_tokens": input_total,
            "output_tokens": output_total,
            "total_tokens": input_total + output_total,
        }
    except Exception as e:
        logger.warning("daily_usage_increment_failed user=%s err=%s", user_id, e)
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


async def get_daily_usage(user_id: str) -> dict:
    """Get the user's current daily token usage."""
    try:
        r = await get_redis()
        input_key = _today_key(user_id, "input")
        output_key = _today_key(user_id, "output")

        input_val = await r.get(input_key)
        output_val = await r.get(output_key)

        input_tokens = int(input_val) if input_val else 0
        output_tokens = int(output_val) if output_val else 0

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
    except Exception as e:
        logger.warning("daily_usage_get_failed user=%s err=%s", user_id, e)
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def get_daily_limit() -> int:
    """Return the daily token limit."""
    return settings.daily_token_limit


async def get_daily_usage_summary(user_id: str) -> dict:
    """Get a full daily usage summary: used, limit, remaining, reset_at."""
    usage = await get_daily_usage(user_id)
    limit = get_daily_limit()
    used = usage["total_tokens"]
    remaining = max(0, limit - used)

    # Reset at next midnight UTC
    now = datetime.now(UTC)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    reset_at = tomorrow.isoformat()

    return {
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "reset_at": reset_at,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
    }
