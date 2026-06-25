from collections.abc import AsyncGenerator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.infrastructure.cache.redis import RedisCache
from app.infrastructure.db.unit_of_work import UnitOfWork
from app.infrastructure.messaging.producer import EventProducer
from app.infrastructure.storage.s3 import S3Storage


async def get_uow(
    session:AsyncSession = Depends(get_db),
) -> AsyncGenerator[UnitOfWork, None]:
    uow = UnitOfWork(session)
    try:
        yield uow
    finally:
        if uow.session.is_active:
            await uow.rollback()
        await uow.session.close()


async def get_producer() -> EventProducer:
    return EventProducer()


async def get_storage() -> S3Storage:
    return S3Storage()


async def get_cache() -> RedisCache:
    return RedisCache()
