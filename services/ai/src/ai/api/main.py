from collections.abc import AsyncGenerator

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.api.dependencies.auth import invalidate_jwks_cache
from ai.api.dependencies.backpressure import init_backpressure
from ai.api.middleware.backpressure import BackpressureMiddleware
from ai.api.middleware.prometheus import PrometheusMiddleware
from ai.api.middleware.request_id import RequestIDMiddleware
from ai.application.admin.model_registry import ModelRegistry
from ai.core.config import settings
from ai.core.logging import setup_logging
from ai.infrastructure.cache.redis_client import close_redis
from ai.infrastructure.db.database import close_db, init_db
from ai.infrastructure.messaging.kafka_producer import get_event_producer
from ai.monitoring.metrics import setup_metrics


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    setup_logging()
    setup_metrics(app)
    init_backpressure()
    await init_db()
    await ModelRegistry.reload()
    await get_event_producer().start()
    invalidate_jwks_cache()
    yield
    await get_event_producer().stop()
    await close_redis()
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Kraivor AI Service",
        description="Multi-agent AI system with RAG, streaming, and per-user key provisioning",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    app.add_middleware(BackpressureMiddleware)
    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(RequestIDMiddleware)

    from ai.api.routers import (
        admin,
        analysis,
        api_keys,
        byok,
        chat,
        conversations,
        embeddings,
        health,
        knowledge,
    )

    app.include_router(health.router, prefix="/v1")
    app.include_router(chat.router, prefix="/v1")
    app.include_router(byok.router, prefix="/v1")
    app.include_router(embeddings.router, prefix="/v1")
    app.include_router(api_keys.router, prefix="/v1")
    app.include_router(analysis.router)
    app.include_router(conversations.router, prefix="/v1")
    app.include_router(knowledge.router, prefix="/v1")
    app.include_router(admin.router)

    return app


app = create_app()
