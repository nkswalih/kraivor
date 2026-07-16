import hmac
import time
from threading import Lock

import jwt
import structlog
from fastapi import HTTPException, Request
from jwt import PyJWKClient
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()

logger = structlog.get_logger(__name__)


class JWTPayload(BaseModel):
    sub: str
    email: str
    workspace_ids: list[str] = []
    roles: dict[str, object] = {}


_jwks_client: PyJWKClient | None = None
_jwks_client_lock = Lock()
_jwks_client_ttl: float = 0


def _get_jwks_client() -> PyJWKClient:
    """Get or create a PyJWKClient with cache TTL management."""
    global _jwks_client, _jwks_client_ttl

    now = time.time()
    if (
        _jwks_client is not None
        and (now - _jwks_client_ttl) < settings.jwt.jwks_cache_ttl
    ):
        return _jwks_client

    with _jwks_client_lock:
        # Double-check inside lock
        if (
            _jwks_client is not None
            and (now - _jwks_client_ttl) < settings.jwt.jwks_cache_ttl
        ):
            return _jwks_client

        try:
            client = PyJWKClient(
                str(settings.jwt.jwks_url),
                cache_keys=True,
                max_cached_keys=16,
                timeout=10,
            )
            # Force initial fetch to validate connectivity
            client.fetch_data()
            _jwks_client = client
            _jwks_client_ttl = now
            return _jwks_client
        except Exception as e:
            logger.error(f"Failed to initialize JWKS client: {e}")
            if _jwks_client is not None:
                return _jwks_client
            raise HTTPException(status_code=503, detail="JWKS unavailable") from e


def invalidate_jwks_cache() -> None:
    """Clear the JWKS client cache."""
    global _jwks_client, _jwks_client_ttl
    with _jwks_client_lock:
        _jwks_client = None
        _jwks_client_ttl = 0


def _verify_token(token: str) -> dict[str, object]:
    """Verify JWT token using JWKS from Identity Service."""
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=[settings.jwt.algorithm],
        audience=settings.jwt.audience,
        issuer=settings.jwt.issuer,
        options={"verify_exp": settings.jwt.verify_expiration},
    )
    return payload


def get_current_user(request: Request) -> JWTPayload:
    """
    FastAPI dependency that verifies JWT token and returns the payload.
    """
    # Skip JWT verification for internal requests (from gateway)
    header_value = request.headers.get(settings.jwt.internal_request_header)
    internal_secret = settings.jwt.internal_request_secret
    if header_value and internal_secret and hmac.compare_digest(
        header_value.encode(), internal_secret.encode()
    ):
        return JWTPayload(
            sub=request.headers.get("X-User-ID", ""),
            email=request.headers.get("X-Email", ""),
            workspace_ids=(
                request.headers.get("X-Workspace-IDs", "").split(",")
                if request.headers.get("X-Workspace-IDs")
                else []
            ),
            roles={},
        )

    # Get the Authorization header
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "missing_authorization",
                "message": "Authorization header required",
            },
        )

    token = auth_header[7:]  # Remove 'Bearer ' prefix

    try:
        payload = _verify_token(token)
        return JWTPayload(
            sub=payload.get("sub") or payload.get("user_id") or "",  # type: ignore[arg-type]
            email=payload.get("email", ""),  # type: ignore[arg-type]
            workspace_ids=payload.get("workspace_ids", []),  # type: ignore[arg-type]
            roles=payload.get("roles", {}),  # type: ignore[arg-type]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail={"error": "token_expired", "message": "Token has expired"},
        ) from None
    except jwt.InvalidTokenError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=401,
            detail={"error": "invalid_token", "message": "Invalid or malformed token"},
        ) from e
    except Exception as e:
        logger.error(f"JWT verification error: {e}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "verification_failed",
                "message": "Token verification failed",
            },
        ) from e
