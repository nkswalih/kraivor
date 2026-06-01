"""
Test settings for Core Service
"""

from . import base as base_settings
from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = "test-secret-key"

ALLOWED_HOSTS = ["*"]

MIDDLEWARE = [
    m for m in base_settings.MIDDLEWARE
    if m != "core.middleware.jwt_auth.JWTAuthenticationMiddleware"
]

# =============================================================================
# DATABASE
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": base_settings.env("POSTGRES_DB", default="kraivor"),
        "USER": base_settings.env("POSTGRES_USER", default="kraivor"),
        "PASSWORD": base_settings.env("POSTGRES_PASSWORD", default="kraivor"),
        "HOST": base_settings.env("DB_HOST", default="localhost"),
        "PORT": base_settings.env.int("DB_PORT", default=5433),
        "TEST": {
            "NAME": "test_kraivor_core",
        },
    }
}

# =============================================================================
# PASSWORDS
# =============================================================================

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# =============================================================================
# EMAIL
# =============================================================================

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# =============================================================================
# CACHE
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# =============================================================================
# CELERY
# =============================================================================

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# =============================================================================
# JWT SETTINGS
# =============================================================================

IDENTITY_JWKS_URL = "http://localhost:8001/.well-known/jwks.json"

JWT_ALGORITHM = "RS256"
JWT_AUDIENCE = "kraivor"
JWT_ISSUER = "kraivor-identity"
JWT_VERIFY_EXPIRATION = True
JWT_JWKS_CACHE_TTL = 3600

INTERNAL_REQUEST_HEADER = "X-Internal-Request"

# =============================================================================
# TEST OPTIMIZATIONS
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
}

# Faster tests
MIGRATION_MODULES = {}

# Force Celery to run tasks synchronously during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_STORE_EAGER_RESULT = True
