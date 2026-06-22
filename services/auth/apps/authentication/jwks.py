from pathlib import Path

import base64
import hashlib
import logging
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

        keys = []

        # Current signing key (always served)
        current_key = cls._load_public_key()
        current_kid = getattr(settings, "JWT_KEY_ID", None)
        keys.append(cls._public_key_to_jwk(current_key, kid=current_kid))

        # Previous key during rotation overlap (if it exists)
        prev_path = getattr(settings, "JWT_PREV_PUBLIC_KEY_PATH", None)
        if prev_path:
            prev_path_obj = Path(prev_path)
            if prev_path_obj.exists():
                try:
                    prev_key = cls._load_public_key_from_path(prev_path_obj)
                    prev_kid = "kraivor-rs256-" + hashlib.sha256(
                        prev_path_obj.read_bytes()
                    ).hexdigest()[:8]
                    keys.append(cls._public_key_to_jwk(prev_key, kid=prev_kid))
                except Exception as exc:
                    logger.warning("Failed to load previous key %s: %s", prev_path, exc)

        cls._cached_jwks = {"keys": keys}
        return cls._cached_jwks

    @classmethod
    def _load_public_key(cls):
        return cls._load_public_key_from_path(Path(settings.JWT_PUBLIC_KEY_PATH))

    @classmethod
    def _load_public_key_from_path(cls, key_path: Path):
        if not key_path.exists():
            raise FileNotFoundError(f"Public key not found at {key_path}")
        with open(key_path, "rb") as f:
            return serialization.load_pem_public_key(f.read())

    @classmethod
    def _public_key_to_jwk(cls, public_key: rsa.RSAPublicKey, kid: str = None) -> dict:
        public_numbers = public_key.public_numbers()

        n_bytes = public_numbers.n.to_bytes(
            (public_numbers.n.bit_length() + 7) // 8, "big"
        )
        e_bytes = public_numbers.e.to_bytes(
            (public_numbers.e.bit_length() + 7) // 8, "big"
        )

        if kid is None:
            key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            kid = "kraivor-rs256-" + hashlib.sha256(key_pem).hexdigest()[:8]

        return {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": kid,
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
