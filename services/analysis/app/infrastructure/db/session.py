from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()


def create_engine() -> AsyncEngine:
    """Create the async SQLAlchemy engine from settings."""
    return create_async_engine(
        settings.database.url.get_secret_value(),
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_recycle=settings.database.pool_recycle,
        echo=settings.database.echo,
        pool_pre_ping=True,
    )


engine = create_engine()

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Session is automatically closed when the request finishes.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
