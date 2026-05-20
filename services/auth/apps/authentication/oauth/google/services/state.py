"""
authentication/oauth/google/services/state.py

CSRF state token management for Google OAuth.

Flow:
  1. generate() → creates a random token, stores it in Redis with TTL
  2. consume(state) → atomically validates + deletes (prevents replay)
  3. Any Redis failure → deny the request (fail-closed security posture)
"""

from __future__ import annotations

import logging
import secrets

import redis
from authentication.oauth.base import OAuthStateService
from django.conf import settings

logger = logging.getLogger(__name__)

GOOGLE_STATE_PREFIX = "oauth:google:state:"


class GoogleStateService(OAuthStateService):
    """
    Redis-backed CSRF state token for Google OAuth.

    State token is a 32-byte cryptographically random hex string.
    Stored in Redis with a configurable TTL (default 10 minutes).
    Consumed on first use — prevents replay attacks.
    """

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        if redis_client is not None:
            self._redis = redis_client
        else:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self._ttl: int = getattr(settings, "OAUTH_STATE_EXPIRE_SECONDS", 600)

    def _key(self, state: str) -> str:
        return f"{GOOGLE_STATE_PREFIX}{state}"

    def generate(self) -> str:
        """
        Generate a new CSRF state token and persist it in Redis.

        Returns the token string to be included in the OAuth redirect URL.
        Raises RuntimeError if Redis is unavailable (fail-closed).
        """
        state = secrets.token_hex(32)
        key = self._key(state)
        try:
            self._redis.setex(key, self._ttl, "1")
        except redis.exceptions.RedisError as exc:
            logger.error("google_oauth_state_generate_failed: %s", exc)
            raise RuntimeError("Unable to generate OAuth state token") from exc
        return state

    def validate(self, state: str) -> bool:
        """Check existence WITHOUT consuming. Use consume() in the callback."""
        if not state:
            return False
        try:
            return bool(self._redis.exists(self._key(state)))
        except redis.exceptions.RedisError as exc:
            logger.error("google_oauth_state_validate_failed: %s", exc)
            return False

    def consume(self, state: str) -> bool:
        """
        Atomically validate and delete the state token.

        Returns True only if the token existed and was successfully deleted.
        A second call with the same token returns False (replay protection).
        """
        if not state:
            return False
        key = self._key(state)
        try:
            deleted = self._redis.delete(key)
            return deleted == 1
        except redis.exceptions.RedisError as exc:
            logger.error("google_oauth_state_consume_failed: %s", exc)
            return False  # fail-closed
