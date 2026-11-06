from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from analysis.api.dependencies.database import get_db
from analysis.infrastructure.cache.redis import RedisCache
from analysis.infrastructure.db.unit_of_work import UnitOfWork
from analysis.infrastructure.messaging.producer import EventProducer
from analysis.infrastructure.storage.s3 import S3Storage


async def get_uow(
    session: AsyncSession = Depends(get_db),
) -> AsyncGenerator[UnitOfWork]:
    uow = UnitOfWork(session)
    await uow.__aenter__()
    try:
        yield uow
    except BaseException:
        await uow.__aexit__(*__import__("sys").exc_info())
        raise
    await uow.__aexit__(None, None, None)


async def get_producer() -> EventProducer:
    return EventProducer()


async def get_storage() -> S3Storage:
    return S3Storage()


async def get_cache() -> RedisCache:
    return RedisCache()
