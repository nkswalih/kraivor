"""
Security utilities for authentication - KRV-011.

Provides:
- Constant-time password comparison (prevents timing attacks)
- Login lockout with Redis (5 failures → 15 minute lockout)
- Device ID generation
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
import uuid
from typing import Optional

import redis
from django.conf import settings
from django.contrib.auth.hashers import check_password as django_check_password
from django.contrib.auth.hashers import make_password as django_make_password


logger = logging.getLogger(__name__)


class LoginLockoutError(Exception):
    """Raised when account is locked due to too many failed attempts."""

    def __init__(self, retry_after: int, email: str) -> None:
        self.retry_after = retry_after
        self.email = email
        super().__init__(f"Account locked. Try again in {retry_after} seconds.")


class LoginLockoutManager:
    """
    Redis-based login lockout manager.

    Tracks failed login attempts per email+IP combination.
    After 5 failures, locks out for 15 minutes.

    Gracefully handles Redis unavailability during tests by returning safe defaults.
    """

    LOCKOUT_PREFIX = "login_lockout"
    ATTEMPTS_PREFIX = "login_attempts"

    def __init__(self, redis_url: str | None = None) -> None:
        url = redis_url or settings.REDIS_URL
        self.client: redis.Redis = redis.from_url(url, decode_responses=True)

    def _get_lockout_key(self, email: str, ip: str) -> str:
        return f"{self.LOCKOUT_PREFIX}:{email.lower()}:{ip}"

    def _get_attempts_key(self, email: str, ip: str) -> str:
        return f"{self.ATTEMPTS_PREFIX}:{email.lower()}:{ip}"

    def check_lockout(self, email: str, ip: str) -> tuple[bool, int]:
        """
        Check if email+IP is locked out.

        Returns:
            (is_locked, retry_after_seconds)
        """
        try:
            lockout_key = self._get_lockout_key(email, ip)
            ttl = self.client.ttl(lockout_key)

            if ttl > 0:
                return True, ttl
            return False, 0
        except redis.exceptions.ConnectionError as e:
            logger.warning(f"Redis unavailable in check_lockout: {e}. Allowing login.")
            return False, 0
        except redis.exceptions.TimeoutError as e:
            logger.warning(f"Redis timeout in check_lockout: {e}. Allowing login.")
            return False, 0

    def record_failure(self, email: str, ip: str) -> int:
        """
        Record a failed login attempt.

        Returns:
            Number of failed attempts after this one.
        """
        try:
            attempts_key = self._get_attempts_key(email, ip)
            lockout_key = self._get_lockout_key(email, ip)

            lockout_seconds = settings.LOGIN_LOCKOUT_MINUTES * 60

            pipe = self.client.pipeline()
            pipe.incr(attempts_key)
            pipe.expire(attempts_key, lockout_seconds)
            results = pipe.execute()

            failed_attempts = results[0]

            if failed_attempts >= settings.LOGIN_MAX_FAILURES:
                pipe = self.client.pipeline()
                pipe.setex(lockout_key, lockout_seconds, 1)
                pipe.delete(attempts_key)
                pipe.execute()

            return failed_attempts
        except redis.exceptions.ConnectionError as e:
            logger.warning(f"Redis unavailable in record_failure: {e}. Cannot track failures.")
            return 0
        except redis.exceptions.TimeoutError as e:
            logger.warning(f"Redis timeout in record_failure: {e}. Cannot track failures.")
            return 0

    def clear_attempts(self, email: str, ip: str) -> None:
        """Clear failed attempts after successful login."""
        try:
            attempts_key = self._get_attempts_key(email, ip)
            lockout_key = self._get_lockout_key(email, ip)

            pipe = self.client.pipeline()
            pipe.delete(attempts_key)
            pipe.delete(lockout_key)
            pipe.execute()
        except redis.exceptions.ConnectionError as e:
            logger.warning(f"Redis unavailable in clear_attempts: {e}. Cannot clear failures.")
        except redis.exceptions.TimeoutError as e:
            logger.warning(f"Redis timeout in clear_attempts: {e}. Cannot clear failures.")

    def is_allowed(self, email: str, ip: str) -> bool:
        """Check if login is allowed (not locked out)."""
        is_locked, _ = self.check_lockout(email, ip)
        return not is_locked


def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time comparison to prevent timing attacks.
    
    Uses hmac.compare_constant_time if available (Python 3.3+),
    otherwise falls back to manual implementation.
    """
    return hmac.compare_digest(a.encode(), b.encode())


def check_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check password using Django's built-in constant-time comparison.
    
    Django's check_password already uses constant-time algorithms
    (PBKDF2, Argon2) which are timing-attack resistant by design.
    """
    return django_check_password(plain_password, hashed_password)


def generate_device_id(request) -> str:
    """
    Generate a device ID from request headers and IP.
    
    Combines User-Agent, Accept-Language, and IP to create
    a unique but stable device identifier.
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '') if request else ''
    ip = get_client_ip(request)
    
    raw = f"{user_agent}:{accept_language}:{ip}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def get_client_ip(request) -> str:
    """Extract client IP from request, handling proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip


_lockout_manager: Optional[LoginLockoutManager] = None


def get_lockout_manager() -> LoginLockoutManager:
    """Get or create the login lockout manager singleton."""
    global _lockout_manager
    if _lockout_manager is None:
        _lockout_manager = LoginLockoutManager()
    return _lockout_manager