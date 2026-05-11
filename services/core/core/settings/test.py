"""
Test settings for Core Service
"""

from .base import *  # noqa: F401, F403, F405

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

IDENTITY_JWKS_URL = "http://localhost:8001/.well-known/jwks.json"
JWT_ALGORITHM = "RS256"
JWT_AUDIENCE = "kraivor"
JWT_ISSUER = "kraivor-identity"
JWT_VERIFY_EXPIRATION = True
JWT_JWKS_CACHE_TTL = 3600
INTERNAL_REQUEST_HEADER = "X-Internal-Request"