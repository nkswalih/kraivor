import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp
from app.monitoring.metrics import http_requests, http_duration


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        http_requests.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()

        http_duration.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        return response
