"""Backpressure: limits concurrent LLM chains to prevent resource exhaustion.

On a t3.medium (2 vCPU, 4GB RAM) with 2 uvicorn workers:
- Max 10 concurrent LLM chains (each holds a DB connection for 5-30s)
- Max 30 total concurrent HTTP requests
- Returns 503 with queue position when at capacity
"""

import asyncio
import logging
import time
from fastapi import HTTPException

logger = logging.getLogger(__name__)

_llm_semaphore: asyncio.Semaphore | None = None
_request_counter: int = 0
_start_time: float = time.monotonic()

MAX_CONCURRENT_LLM_CHAINS = 10
MAX_CONCURRENT_REQUESTS = 30
LLM_CHAIN_TIMEOUT_SECONDS = 90


def init_backpressure(max_llm: int = MAX_CONCURRENT_LLM_CHAINS, max_requests: int = MAX_CONCURRENT_REQUESTS) -> None:
    global _llm_semaphore, _start_time
    _llm_semaphore = asyncio.Semaphore(max_llm)
    _start_time = time.monotonic()
    logger.info(
        "backpressure_initialized max_llm_chains=%d max_concurrent_requests=%d",
        max_llm,
        max_requests,
    )


async def acquire_llm_slot() -> None:
    """Acquire a slot for an LLM chain. Raises 503 if at capacity."""
    global _request_counter

    if _llm_semaphore is None:
        return

    _request_counter += 1
    if _request_counter > MAX_CONCURRENT_REQUESTS:
        _request_counter -= 1
        raise HTTPException(
            status_code=503,
            detail={
                "error": "system_overloaded",
                "message": "Too many concurrent requests. Please retry in a few seconds.",
                "retry_after": 5,
            },
        )

    if _llm_semaphore.locked():
        waiting = MAX_CONCURRENT_LLM_CHAINS - _llm_semaphore._value
        logger.warning(
            "backpressure_llm_queue depth=%d", waiting
        )


async def release_llm_slot() -> None:
    global _request_counter
    _request_counter = max(0, _request_counter - 1)


def get_backpressure_stats() -> dict:
    """Return current backpressure stats for the health endpoint."""
    available = _llm_semaphore._value if _llm_semaphore else MAX_CONCURRENT_LLM_CHAINS
    uptime = time.monotonic() - _start_time
    return {
        "concurrent_llm_chains": MAX_CONCURRENT_LLM_CHAINS - available,
        "max_llm_chains": MAX_CONCURRENT_LLM_CHAINS,
        "concurrent_requests": _request_counter,
        "max_concurrent_requests": MAX_CONCURRENT_REQUESTS,
        "uptime_seconds": int(uptime),
    }
