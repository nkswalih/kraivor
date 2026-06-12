import jwt
import logging
from django.conf import settings
from django.http import JsonResponse
from jwt import PyJWKClient
from threading import Lock

logger = logging.getLogger(__name__)

# ── Module-level JWKS client cache ───────────────────────────────────────────
# PyJWKClient must be a singleton — not created per-request.
# Creating per-request hammers the identity service with JWKS fetches.
_jwks_client: PyJWKClient | None = None
_jwks_client_lock = Lock()


def _get_jwks_client() -> PyJWKClient:
    """
    Return cached PyJWKClient. Create on first call.

    PyJWKClient already handles internal key caching and TTL via
    lifespan_seconds. We wrap it in a module-level singleton so the
    same client (and its key cache) is reused across all requests.
    """
    global _jwks_client
    if _jwks_client is None:
        with _jwks_client_lock:
            if _jwks_client is None:  # double-checked locking
                _jwks_client = PyJWKClient(
                    settings.IDENTITY_JWKS_URL,
                    cache_keys=True,
                    lifespan=getattr(settings, "JWT_JWKS_CACHE_TTL", 3600),
                )
                logger.info("jwks_client.created url=%s", settings.IDENTITY_JWKS_URL)
    return _jwks_client


class JWTAuthenticationMiddleware:
    """
    Verify RS256 JWT tokens issued by the Identity Service.

    Flow:
      1. Skip internal requests (X-Internal-Request header)
      2. Skip admin / health paths
      3. Extract Bearer token
      4. Verify via JWKS — handles RS256 + kid lookup automatically
      5. Set request.user_id / .email / .workspace_ids / .roles

    Token must have `kid` header matching a key in the JWKS endpoint.
    If identity service signs without `kid`, see identity service fix below.
    """

    # Paths that bypass auth entirely
    _EXEMPT_PATHS = (
        "/api/github-app/callback/",
        "/api/github-app/webhook/",
        "/api/health/",
    )
    _SKIP_PREFIXES = ("/admin/", "/health/", "/api/health/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ── Skip: exempt paths (no JWT required) ────────────────────────────
        if any(request.path.startswith(p) for p in self._EXEMPT_PATHS):
            return self.get_response(request)

        # ── Skip: internal gateway request ───────────────────────────────────
        if request.headers.get(settings.INTERNAL_REQUEST_HEADER):
            return self.get_response(request)

        # ── Skip: public paths ────────────────────────────────────────────────
        if any(request.path.startswith(p) for p in self._SKIP_PREFIXES):
            return self.get_response(request)

        # ── Extract Bearer token ──────────────────────────────────────────────
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JsonResponse(
                {
                    "error": "missing_authorization",
                    "message": "Authorization header required",
                },
                status=401,
            )

        token = auth_header[7:]

        # ── Verify ────────────────────────────────────────────────────────────
        try:
            payload = self._verify_token(token)

        except jwt.ExpiredSignatureError:
            return JsonResponse(
                {"error": "token_expired", "message": "Token has expired"}, status=401
            )
        except jwt.InvalidTokenError as exc:
            logger.warning("jwt.invalid token=%s...: %s", token[:20], exc)
            return JsonResponse(
                {"error": "invalid_token", "message": "Invalid or malformed token"},
                status=401,
            )
        except Exception as exc:
            logger.error("jwt.verification_failed: %s", exc, exc_info=True)
            return JsonResponse(
                {
                    "error": "verification_failed",
                    "message": "Token verification failed",
                },
                status=401,
            )

        # ── Attach to request ─────────────────────────────────────────────────
        request.jwt_payload = payload
        request.user_id = payload.get("sub") or payload.get("user_id")
        request.user_name = payload.get("name") or payload.get("email", "")
        request.email = payload.get("email")
        request.user_email = payload.get("email")
        request.workspace_ids = payload.get("workspace_ids", [])
        request.roles = payload.get("roles", {})

        return self.get_response(request)

    def _verify_token(self, token: str) -> dict:
        """
        Verify JWT using JWKS.

        PyJWKClient.get_signing_key_from_jwt() reads the `kid` from the
        token header and matches it against keys in the JWKS endpoint.

        Error 'Unable to find a signing key that matches: "None"' means
        the token was issued WITHOUT a `kid` header. Fix is in the identity
        service (see comment below), NOT here.

        Fallback: if kid is None and only one key exists in JWKS, we can
        fetch all keys and use the first one. Enabled via
        settings.JWT_ALLOW_NO_KID = True (dev only, never production).
        """
        client = _get_jwks_client()

        # ── Primary path: token has kid ───────────────────────────────────────
        try:
            signing_key = client.get_signing_key_from_jwt(token)

        except Exception:
            # ── Fallback: no kid in token (dev / misconfigured identity svc) ──
            # Only attempt if explicitly allowed AND there's exactly one key.
            # This is UNSAFE for production — disable once identity svc fixed.
            if getattr(settings, "JWT_ALLOW_NO_KID", False):
                signing_key = self._get_single_key_fallback(client, token)
            else:
                raise

        decode_options = {
            "verify_exp": getattr(settings, "JWT_VERIFY_EXPIRATION", True)
        }

        # Only verify audience/issuer if configured
        audience = getattr(settings, "JWT_AUDIENCE", None)
        issuer = getattr(settings, "JWT_ISSUER", None)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[settings.JWT_ALGORITHM],
            audience=audience,
            issuer=issuer,
            options=decode_options,
        )

        return payload

    @staticmethod
    def _get_single_key_fallback(client: PyJWKClient, token: str):
        """
        Fallback when token has no `kid`.

        Fetch fresh JWKS and use the only key present.
        Raises ValueError if multiple keys exist (ambiguous — can't guess).

        Use only in development. Production tokens must have `kid`.
        """
        client.fetch_data()  # force-refresh key cache
        jwk_data = client.get_jwk_set()
        keys = list(jwk_data.keys)

        if not keys:
            raise jwt.InvalidTokenError("JWKS endpoint returned no keys")
        if len(keys) > 1:
            raise jwt.InvalidTokenError(
                f"Token has no kid but JWKS has {len(keys)} keys — cannot determine which to use. "
                "Fix identity service to include kid in JWT header."
            )

        logger.warning(
            "jwt.no_kid_fallback used — token missing kid header. "
            "Fix identity service to include kid when signing tokens."
        )
        return keys[0]

    @staticmethod
    def invalidate_cache() -> None:
        """Clear the module-level JWKS client cache."""
        global _jwks_client
        with _jwks_client_lock:
            _jwks_client = None
