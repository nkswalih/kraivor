"""
JWT Utilities - Legacy compatibility layer
==========================================

This module provides backward compatibility for code that references
the old jwt.py functions. New code should use tokens.py directly.

DEPRECATED: Use tokens.py for new implementations.
"""

from .tokens import (
    TokenPair,
    TokenPayload,
    get_token_service,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    TokenReusedError,
    CustomRefreshToken,
)

from .cookie_utils import create_refresh_cookie, clear_refresh_cookie


def generate_token_pair(user, device_id: str = "", ip: str = "", user_agent: str = ""):
    """
    Generate access and refresh token pair.
    
    DEPRECATED: Use TokenService.generate_tokens() instead.
    This function is maintained for backward compatibility.
    """
    token_service = get_token_service()
    token_pair = token_service.generate_tokens(
        user=user,
        device_id=device_id,
        ip_address=ip,
        user_agent=user_agent,
    )
    
    return {
        'access_token': token_pair.access_token,
        'refresh_token': token_pair.refresh_token,
        'token_type': token_pair.token_type,
        'expires_in': token_pair.expires_in,
    }


def create_refresh_cookie_deprecated(refresh_token: str) -> dict:
    """
    Create refresh token cookie settings.
    
    DEPRECATED: Use create_refresh_cookie from cookie_utils instead.
    """
    return create_refresh_cookie(refresh_token)


def decode_refresh_token(token: str):
    """
    Decode refresh token payload.
    
    DEPRECATED: Use TokenService.validate_only() instead.
    """
    token_service = get_token_service()
    payload = token_service.validate_only(token)
    
    return {
        'user_id': payload.user_id,
        'email': payload.email,
        'name': payload.name,
        'device_id': payload.device_id,
    }


__all__ = [
    'TokenPair',
    'TokenPayload',
    'get_token_service',
    'TokenError',
    'TokenExpiredError',
    'TokenInvalidError',
    'TokenRevokedError',
    'TokenReusedError',
    'CustomRefreshToken',
    'create_refresh_cookie',
    'clear_refresh_cookie',
    'generate_token_pair',
    'create_refresh_cookie_deprecated',
    'decode_refresh_token',
]