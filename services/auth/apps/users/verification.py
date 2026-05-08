"""
Email verification JWT token utilities.

Generates and validates signed JWTs for email verification following production
standards. Tokens are stateless — no DB storage required.

Token claims:
  sub           → user UUID (string)
  email         → user email
  token_type    → "email_verification"  (prevents reuse across flows)
  iat           → issued-at (UTC)
  exp           → expires-at (UTC, 24 h)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt
from django.conf import settings

if TYPE_CHECKING:
    from apps.users.models import User

_ALGORITHM = "HS256"
_TOKEN_TYPE = "email_verification"
_EXPIRY_HOURS = 24


def generate_verification_token(user: User) -> str:
    """Return a signed JWT for the given user's email verification."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "token_type": _TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(hours=_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def decode_verification_token(token: str) -> tuple[dict, str | None]:
    """
    Decode and validate an email verification JWT.

    Returns:
        (payload, None)            on success
        ({},      error_code)      on failure

    Error codes:
        "token_expired"   — JWT exp has passed
        "invalid_token"   — any other JWT error or wrong token_type
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {}, "token_expired"
    except jwt.InvalidTokenError:
        return {}, "invalid_token"

    if payload.get("token_type") != _TOKEN_TYPE:
        return {}, "invalid_token"

    return payload, None
