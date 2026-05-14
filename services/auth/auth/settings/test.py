"""
Django Test Settings
=====================

Configuration for running tests with pytest.

Usage:
    pytest                    # Run all tests
    pytest --cov             # With coverage
    pytest tests/test_*.py   # Specific files
"""
import os

os.environ.setdefault("DJANGO_TEST_MODE", "1")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-do-not-use-in-production")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", ".keys/jwt-private.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", ".keys/jwt-public.pem")
os.environ.setdefault("JWT_ALGORITHM", "RS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("EMAIL_BACKEND", "django.core.mail.backends.locmem.EmailBackend")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_PORT", "1025")
os.environ.setdefault("EMAIL_USE_TLS", "False")
os.environ.setdefault("EMAIL_USE_SSL", "False")
os.environ.setdefault("EMAIL_FROM", "noreply@kraivor.test")

from .base import *

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

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/15")

REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    "rest_framework.authentication.SessionAuthentication",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "RequireDebugFalse": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "RequireDebugTrue": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "authentication": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

SECRET_KEY = "test-secret-key-for-testing-only-do-not-use-in-production"
