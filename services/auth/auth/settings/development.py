"""
Django Development Settings
============================

Development-specific configuration optimized for local development.
Uses local services (Mailhog, local PostgreSQL, Redis) and enables
debugging features.

Key Differences from Production:
- DEBUG = True (shows detailed error pages)
- Allows localhost origins for CORS
- Uses local services (Mailhog, local DB)
- Relaxed security settings for ease of development
- Auto-reloading enabled

Environment Variables:
- All values come from .env file
- Sensible defaults provided for common dev scenarios
- Override any setting with environment variables
"""

import os
from pathlib import Path

import environ

# =============================================================================
# .env Discovery — works on local AND inside Docker
# =============================================================================
# Problem with parents[4]:
#   Local:  C:/VS Code/kraivor/services/auth/auth/settings/development.py
#           parents[4] = C:/VS Code/kraivor  ← .env lives here ✓
#
#   Docker: /app/auth/settings/development.py
#           parents[2] = /app                ← only 3 levels exist, [4] crashes ✗
#
# Fix: walk up the tree and stop at the first .env found.
# In Docker, compose already injected env vars via env_file — environ.Env.read_env
# is a no-op when the vars are already set, so this is safe either way.

def _find_env_file(start: Path) -> Path | None:
    """Walk up from start until a .env file is found or we hit the filesystem root."""
    for parent in start.parents:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return None

_HERE = Path(__file__).resolve()
_env_file = _find_env_file(_HERE)
if _env_file:
    environ.Env.read_env(_env_file)

# =============================================================================
# Defaults — only applied when env var is not already set
# (Docker compose env_file injection takes priority over these)
# =============================================================================
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql://kraivor:kraivor@localhost:5433/kraivor")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", ".keys/jwt-private.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", ".keys/jwt-public.pem")
os.environ.setdefault("JWT_ALGORITHM", "RS256")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_PORT", "1025")
os.environ.setdefault("EMAIL_USE_TLS", "False")
os.environ.setdefault("EMAIL_USE_SSL", "False")
os.environ.setdefault("EMAIL_FROM", "noreply@kraivor.local")

from .base import *  # noqa: F401, F403, F405

# =============================================================================
# DEBUG MODE
# =============================================================================
DEBUG = True

# =============================================================================
# ALLOWED HOSTS - Development
# =============================================================================
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "localhost",
        "127.0.0.1",
        "127.0.0.1:3000",
        "localhost:3000",
        "127.0.0.1:8001",
        "localhost:8001",
    ],
)

# =============================================================================
# CORS - Development
# =============================================================================
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=True)
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)

# =============================================================================
# EMAIL - Development (Mailhog)
# =============================================================================
# Mailhog catches all outgoing email.
# Web UI: http://localhost:8025
# In Docker: EMAIL_HOST=mailhog is injected by compose, overrides the default below.
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_STARTTLS = env.bool("EMAIL_USE_STARTTLS", default=False)
EMAIL_FROM = env("EMAIL_FROM", default="noreply@kraivor.local")

# =============================================================================
# FRONTEND URL
# =============================================================================
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# =============================================================================
# COOKIES - Development
# =============================================================================
# Secure=False so cookies work over plain HTTP in dev.
COOKIE_SECURE = env.bool("COOKIE_SECURE", default=False)
COOKIE_DOMAIN = env("COOKIE_DOMAIN", default="")
COOKIE_SAMESITE = env("COOKIE_SAMESITE", default="Lax")

# =============================================================================
# CACHES - Development (local memory, no Redis needed)
# =============================================================================
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# =============================================================================
# LOGGING - Development (verbose)
# =============================================================================
LOGGING["root"]["level"] = "INFO"

LOGGING["loggers"]["django"]["level"] = "INFO"

LOGGING["loggers"]["django.utils.autoreload"] = {
    "handlers": ["console"],
    "level": "WARNING",
    "propagate": False,
}

LOGGING["loggers"]["django.db.backends"] = {
    "handlers": ["console"],
    "level": "WARNING",
    "propagate": False,
}

LOGGING["loggers"]["authentication"] = {
    "handlers": ["console"],
    "level": "DEBUG",
    "propagate": False,
}

# =============================================================================
# REST FRAMEWORK - Development (adds browsable API)
# =============================================================================
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# =============================================================================
# CELERY - Development (run tasks synchronously, no worker needed)
# =============================================================================
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True