import logging
import time
from typing import Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class JWTPayload(BaseModel):
    sub: str
    email: str
    workspace_ids: list[str] = []
    roles: dict = {}


_jwks_cache: Optional[dict] = None
_jwks_cache_time: float = 0


def _get_jwks() -> dict:
    """Get JWKS from Identity Service with caching."""
    global _jwks_cache, _jwks_cache_time
    now = time.time()

    if _jwks_cache and (now - _jwks_cache_time) < settings.jwt_jwks_cache_ttl:
        return _jwks_cache

    try:
        response = httpx.get(settings.identity_jwks_url, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = now
        return _jwks_cache
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        if _jwks_cache:
            return _jwks_cache
        raise HTTPException(status_code=503, detail="JWKS unavailable")


def _verify_token(token: str) -> dict:
    """Verify JWT token using JWKS from Identity Service."""
    jwks = _get_jwks()
    jwk = jwks['keys'][0]

    payload = jwt.decode(
        token,
        jwk,
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={'verify_exp': settings.jwt_verify_expiration}
    )
    return payload


def get_current_user(request: Request) -> JWTPayload:
    """
    FastAPI dependency that verifies JWT token and returns the payload.
    """
    # Skip JWT verification for internal requests (from gateway)
    if request.headers.get(settings.internal_request_header):
        return JWTPayload(
            sub=request.headers.get("X-User-ID", ""),
            email=request.headers.get("X-Email", ""),
            workspace_ids=request.headers.get("X-Workspace-IDs", "").split(",") if request.headers.get("X-Workspace-IDs") else [],
            roles={}
        )

    # Get the Authorization header
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": "missing_authorization", "message": "Authorization header required"}
        )

    token = auth_header[7:]  # Remove 'Bearer ' prefix

    try:
        payload = _verify_token(token)
        return JWTPayload(
            sub=payload.get("sub", ""),
            email=payload.get("email", ""),
            workspace_ids=payload.get("workspace_ids", []),
            roles=payload.get("roles", {})
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": "token_expired", "message": "Token has expired"}
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Invalid or malformed token"}
        )
    except Exception as e:
        logger.error(f"JWT verification error: {e}")
        raise HTTPException(
            status_code=401,
            detail={"error": "verification_failed", "message": "Token verification failed"}
        )


def invalidate_jwks_cache():
    """Clear the JWKS cache."""
    global _jwks_cache, _jwks_cache_time
    _jwks_cache = None
    _jwks_cache_time = 0