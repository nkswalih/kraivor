"""
OAuth State Manager - CSRF state with Redis
"""

import logging
import secrets
from typing import Optional

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


class OAuthStateError(Exception):
    pass


class OAuthStateManager:
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._state_ttl = getattr(settings, "OAUTH_STATE_EXPIRE_SECONDS", 600)

    @property
    def redis_client(self) -> redis.Redis:
        if self._redis_client is None:
            redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
            self._redis_client = redis.from_url(redis_url, decode_responses=True)
        return self._redis_client

    def generate_state(self, provider: str) -> str:
        state = secrets.token_urlsafe(32)
        key = f"oauth_state:{provider}:{state}"
        try:
            self.redis_client.setex(key, self._state_ttl, "valid")
            return state
        except redis.RedisError as e:
            logger.error("oauth_state_storage_failed", extra={"provider": provider, "error": str(e)})
            raise OAuthStateError("Failed to create OAuth state") from e

    def validate_state(self, provider: str, state: str) -> bool:
        if not state:
            return False
        key = f"oauth_state:{provider}:{state}"
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except redis.RedisError as e:
            logger.error("oauth_state_validation_failed", extra={"provider": provider, "error": str(e)})
            raise OAuthStateError("Failed to validate OAuth state") from e


_state_manager = None


def get_state_manager() -> OAuthStateManager:
    global _state_manager
    if _state_manager is None:
        _state_manager = OAuthStateManager()
    return _state_manager