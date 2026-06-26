import time

import httpx
import jwt
import structlog
from fastapi import HTTPException, Request
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()

logger = structlog.get_logger(__name__)


class JWTPayload(BaseModel):
    sub: str
    email: str
    workspace_ids: list[str] = []
    roles: dict[str, object] = {}


_jwks_cache: dict[str, object] | None = None
_jwks_cache_time: float = 0


def _get_jwks() -> dict[str, object]:
    """Get JWKS from Identity Service with caching."""
    global _jwks_cache, _jwks_cache_time
    now = time.time()

    if _jwks_cache and (now - _jwks_cache_time) < settings.jwt.jwks_cache_ttl:
        return _jwks_cache

    try:
        response = httpx.get(str(settings.jwt.jwks_url), timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_cache_time = now
        return _jwks_cache
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        if _jwks_cache:
            return _jwks_cache
        raise HTTPException(status_code=503, detail="JWKS unavailable") from e


def _verify_token(token: str) -> dict[str, object]:
    """Verify JWT token using JWKS from Identity Service."""
    jwks = _get_jwks()
    jwk = jwks['keys'][0]  # type: ignore[index]

    payload = jwt.decode(
        token,
        jwk,
        algorithms=[settings.jwt.algorithm],
        audience=settings.jwt.audience,
        issuer=settings.jwt.issuer,
        options={'verify_exp': settings.jwt.verify_expiration}
    )
    return payload


def get_current_user(request: Request) -> JWTPayload:
    """
    FastAPI dependency that verifies JWT token and returns the payload.
    """
    # Skip JWT verification for internal requests (from gateway)
    if request.headers.get(settings.jwt.internal_request_header):
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
            sub=payload.get("sub", ""),  # type: ignore[arg-type]
            email=payload.get("email", ""),  # type: ignore[arg-type]
            workspace_ids=payload.get("workspace_ids", []),  # type: ignore[arg-type]
            roles=payload.get("roles", {})  # type: ignore[arg-type]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": "token_expired", "message": "Token has expired"}
        ) from None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Invalid or malformed token"}
        ) from e
    except Exception as e:
        logger.error(f"JWT verification error: {e}")
        raise HTTPException(
            status_code=401,
            detail={"error": "verification_failed", "message": "Token verification failed"}
        ) from e


def invalidate_jwks_cache() -> None:
    """Clear the JWKS cache."""
    global _jwks_cache, _jwks_cache_time
    _jwks_cache = None
    _jwks_cache_time = 0