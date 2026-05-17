import base64
import logging
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.http import JsonResponse
from django.views import View

logger = logging.getLogger(__name__)


class JWKSView(View):
    """Serve the public key in JWK format for JWT verification."""

    _cached_jwks = None

    def get(self, request):
        try:
            jwks = self._get_jwks()
            response = JsonResponse(jwks)
            response["Cache-Control"] = "public, max-age=3600"
            return response
        except FileNotFoundError:
            logger.error("JWKS: Public key not found at %s", settings.JWT_PUBLIC_KEY_PATH)
            return JsonResponse(
                {"error": "Public key not configured", "error_code": "jwks_not_available"},
                status=503,
            )
        except Exception as e:
            logger.exception("JWKS: Unexpected error loading public key: %s", e)
            return JsonResponse(
                {"error": "Failed to load public key", "error_code": "jwks_error"},
                status=500,
            )

    @classmethod
    def _get_jwks(cls):
        if cls._cached_jwks is not None:
            return cls._cached_jwks

        public_key = cls._load_public_key()
        jwks = cls._public_key_to_jwk(public_key)
        cls._cached_jwks = {"keys": [jwks]}
        return cls._cached_jwks

    @classmethod
    def _load_public_key(cls):
        key_path = Path(settings.JWT_PUBLIC_KEY_PATH)
        if not key_path.exists():
            raise FileNotFoundError(f"Public key not found at {key_path}")
        with open(key_path, "rb") as f:
            return serialization.load_pem_public_key(f.read())

    @classmethod
    def _public_key_to_jwk(cls, public_key: rsa.RSAPublicKey) -> dict:
        public_numbers = public_key.public_numbers()
        n_bytes = public_numbers.n.to_bytes(256, "big")
        e_bytes = public_numbers.e.to_bytes(4, "big")

        return {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": "kraivor-key-1",
            "n": cls._base64url_encode(n_bytes),
            "e": cls._base64url_encode(e_bytes),
        }

    @staticmethod
    def _base64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @classmethod
    def invalidate_cache(cls):
        cls._cached_jwks = None


def get_jwks() -> dict:
    return JWKSView._get_jwks()
