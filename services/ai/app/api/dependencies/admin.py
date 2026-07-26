import logging

from fastapi import Depends, HTTPException

from app.api.dependencies.auth import JWTPayload, get_current_user
from app.infrastructure.db.database import async_session_factory
from app.infrastructure.db.models.platform_admin import PlatformAdmin
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def require_superadmin(
    current_user: JWTPayload = Depends(get_current_user),
) -> JWTPayload:
    """Dependency: raises 403 if user is not a platform superadmin."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(PlatformAdmin).where(PlatformAdmin.user_id == current_user.sub)
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=403,
                detail="Superadmin access required",
            )
    return current_user
