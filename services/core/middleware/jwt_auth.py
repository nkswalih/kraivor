import logging
import time

import jwt
import requests
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware:
    """
    Django middleware to verify JWT tokens from the Identity Service.

    Adds X-User-ID, X-Email, X-Workspace-IDs headers to requests
    after successful JWT verification.
    """

    _jwks_cache: dict | None = None
    _jwks_cache_time: float = 0

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip JWT verification for internal requests (from gateway)
        if request.headers.get(settings.INTERNAL_REQUEST_HEADER):
            return self.get_response(request)

        # Skip verification for admin and health endpoints
        if request.path.startswith('/admin/') or request.path.startswith('/health/'):
            return self.get_response(request)

        # Get the Authorization header
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {'error': 'missing_authorization', 'message': 'Authorization header required'},
                status=401
            )

        token = auth_header[7:]  # Remove 'Bearer ' prefix

        try:
            payload = self._verify_token(token)
            request.jwt_payload = payload
            request.user_id = payload.get('sub')
            request.email = payload.get('email')
            request.workspace_ids = payload.get('workspace_ids', [])
            request.roles = payload.get('roles', {})

        except jwt.ExpiredSignatureError:
            return JsonResponse(
                {'error': 'token_expired', 'message': 'Token has expired'},
                status=401
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT validation failed: {e}")
            return JsonResponse(
                {'error': 'invalid_token', 'message': 'Invalid or malformed token'},
                status=401
            )
        except Exception as e:
            logger.error(f"JWT verification error: {e}")
            return JsonResponse(
                {'error': 'verification_failed', 'message': 'Token verification failed'},
                status=401
            )

        return self.get_response(request)

    def _verify_token(self, token: str) -> dict:
        """Verify JWT token using JWKS from Identity Service."""
        jwks = self._get_jwks()
        jwk = jwks['keys'][0]

        payload = jwt.decode(
            token,
            jwk,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={'verify_exp': settings.JWT_VERIFY_EXPIRATION}
        )
        return payload

    def _get_jwks(self) -> dict:
        """Get JWKS from Identity Service with caching."""
        now = time.time()
        cache_ttl = getattr(settings, 'JWT_JWKS_CACHE_TTL', 3600)

        if self._jwks_cache and (now - self._jwks_cache_time) < cache_ttl:
            return self._jwks_cache

        jwks_url = getattr(settings, 'IDENTITY_JWKS_URL', 'http://identity:8001/.well-known/jwks.json')

        try:
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_cache_time = now
            return self._jwks_cache
        except requests.RequestException as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            if self._jwks_cache:
                return self._jwks_cache
            raise

    @classmethod
    def invalidate_cache(cls):
        """Clear the JWKS cache."""
        cls._jwks_cache = None
        cls._jwks_cache_time = 0