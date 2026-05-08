from datetime import datetime, timedelta, timezone
from typing import Optional

from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


class CustomRefreshToken(RefreshToken):
    """Custom refresh token with device_id and extended claims."""

    @classmethod
    def for_user(cls, user, device_id: str = ""):
        token = super().for_user(user)
        token['name'] = user.name
        if device_id:
            token['device_id'] = device_id
        return token


def generate_token_pair(user, device_id: str = "", ip: str = "", user_agent: str = "") -> dict:
    """
    Generate access and refresh token pair.
    
    Returns:
        {
            'access_token': str,
            'refresh_token': str,
            'token_type': 'Bearer',
            'expires_in': int (seconds),
        }
    """
    refresh = CustomRefreshToken.for_user(user, device_id)
    
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    
    # Calculate expiry in seconds
    expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    expires_in = expire_minutes * 60
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': expires_in,
    }


def create_refresh_cookie(refresh_token: str) -> dict:
    """
    Create refresh token cookie settings.
    
    Returns cookie attributes dict for Response.set_cookie()
    """
    max_age = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    
    return {
        'refresh_token': refresh_token,
        'max_age': max_age,
        'httponly': True,
        'secure': not settings.DEBUG,
        'samesite': 'Lax',
        'path': '/auth/',
    }


def decode_refresh_token(token: str) -> Optional[dict]:
    """
    Decode and validate refresh token.
    
    Returns token payload or None if invalid.
    """
    try:
        token_obj = RefreshToken(token)
        return {
            'user_id': str(token_obj.get('user_id')),
            'email': token_obj.get('email'),
            'name': token_obj.get('name'),
            'device_id': token_obj.get('device_id', ''),
        }
    except Exception:
        return None