"""Middleware that tracks concurrent requests and rejects with 503 when at capacity."""

import asyncio
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

MAX_CONCURRENT = 30
_queue_start: float = time.monotonic()
_active: int = 0


class BackpressureMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        global _active

        _active += 1
        try:
            if _active > MAX_CONCURRENT:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "system_overloaded",
                        "message": "Server is at capacity. Please retry in a few seconds.",
                        "retry_after": 5,
                    },
                )
            response = await call_next(request)
            return response
        finally:
            _active = max(0, _active - 1)
