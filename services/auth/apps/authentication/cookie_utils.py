"""
Cookie utilities for secure token handling - KRV-013

Provides consistent cookie configuration across all endpoints.
"""

from typing import Any

from django.conf import settings


def create_refresh_cookie(refresh_token: str, max_age_days: int = None) -> dict[str, Any]:
    """
    Create refresh token cookie settings.

    Returns cookie attributes dict for Response.set_cookie()
    """
    if max_age_days is None:
        max_age_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    max_age_seconds = max_age_days * 24 * 60 * 60

    return {
        "value": refresh_token,
        "max_age": max_age_seconds,
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": settings.COOKIE_PATH,
        "domain": settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None,
    }


def clear_refresh_cookie() -> dict[str, Any]:
    """Create cookie settings to clear the refresh token."""
    return {
        "value": "",
        "max_age": 0,
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": settings.COOKIE_PATH,
        "domain": settings.COOKIE_DOMAIN if settings.COOKIE_DOMAIN else None,
    }
