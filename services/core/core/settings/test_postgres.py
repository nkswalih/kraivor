"""
Test settings for Core Service — PostgreSQL
============================================

Configuration for running tests against a real PostgreSQL database.

Usage (CI):
    DJANGO_SETTINGS_MODULE=core.settings.test_postgres \\
    DATABASE_URL=postgresql://kraivor:kraivor@localhost:5432/kraivor_test \\
    pytest

Differs from test.py by:
  - Not hardcoding DATABASES to SQLite (inherits base.py which reads DATABASE_URL)
  - Not including MIGRATION_MODULES = {} (want to validate migrations against PG)
  - Keeping all other test settings identical (Celery eager, in-memory channels, etc.)
"""

from . import base as base_settings
from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = "test-secret-key"  # nosec - test settings

ALLOWED_HOSTS = ["*"]

MIDDLEWARE = [
    m
    for m in base_settings.MIDDLEWARE
    if m != "core.middleware.jwt_auth.JWTAuthenticationMiddleware"
]

REST_FRAMEWORK = {
    **base_settings.REST_FRAMEWORK,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.middleware.test_auth.TestAuthentication",
    ],
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

IDENTITY_JWKS_URL = "http://localhost:8001/.well-known/jwks.json"

JWT_ALGORITHM = "RS256"
JWT_AUDIENCE = "kraivor"
JWT_ISSUER = "kraivor-identity"
JWT_VERIFY_EXPIRATION = True
JWT_JWKS_CACHE_TTL = 3600

INTERNAL_REQUEST_HEADER = "X-Internal-Request"

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
STORAGES = {
    "default": {"BACKEND": DEFAULT_FILE_STORAGE},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

LOGGING = {"version": 1, "disable_existing_loggers": True}

# Celery
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_STORE_EAGER_RESULT = True

# Channels — In-memory channel layer for tests
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Redis — Disabled in tests (not needed with eager Celery + in-memory channels)
REDIS_URL = None

# DynamoDB — Disabled in tests (use mocks)
DYNAMODB_LOCAL = False
