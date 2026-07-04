# ruff: noqa: F401, F403, F405
"""
Django Test Settings — PostgreSQL
===================================

Configuration for running tests against a real PostgreSQL database.

Usage (CI):
    DJANGO_SETTINGS_MODULE=auth.settings.test_postgres \\
    DATABASE_URL=postgresql://kraivor:kraivor@localhost:5432/kraivor_test \\
    pytest

Differs from test.py by:
  - Not hardcoding DATABASES to SQLite (inherits base.py which reads DATABASE_URL)
  - Not defaulting DATABASE_URL to sqlite://:memory:
  - Keeping all other test settings identical (CACHES, PASSWORD_HASHERS, etc.)
"""

import os
from pathlib import Path

_keys_dir = Path(__file__).resolve().parent.parent.parent / ".keys"
_keys_dir.mkdir(parents=True, exist_ok=True)

for _key_name in ("jwt-private.pem", "jwt-public.pem"):
    if not (_keys_dir / _key_name).exists():
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        _key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        (_keys_dir / "jwt-private.pem").write_bytes(
            _key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
        (_keys_dir / "jwt-public.pem").write_bytes(
            _key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
        break

_oauth_key_path = _keys_dir / "oauth-encryption.key"
if not _oauth_key_path.exists():
    import secrets
    _oauth_key_path.write_text(secrets.token_hex(32))

os.environ.setdefault("JWT_PRIVATE_KEY_PATH", str(_keys_dir / "jwt-private.pem"))
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", str(_keys_dir / "jwt-public.pem"))
os.environ.setdefault("OAUTH_TOKEN_ENCRYPTION_KEY", str(_oauth_key_path))

from .base import *  # noqa: E402

os.environ.setdefault("DJANGO_TEST_MODE", "1")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-do-not-use-in-production")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("JWT_PRIVATE_KEY_PATH", ".keys/jwt-private.pem")
os.environ.setdefault("JWT_PUBLIC_KEY_PATH", ".keys/jwt-public.pem")
os.environ.setdefault("JWT_ALGORITHM", "RS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")
os.environ.setdefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30")
os.environ.setdefault("FRONTEND_URL", "http://localhost")
os.environ.setdefault("EMAIL_BACKEND", "django.core.mail.backends.locmem.EmailBackend")
os.environ.setdefault("EMAIL_HOST", "localhost")
os.environ.setdefault("EMAIL_PORT", "1025")
os.environ.setdefault("EMAIL_USE_TLS", "False")
os.environ.setdefault("EMAIL_USE_SSL", "False")
os.environ.setdefault("EMAIL_FROM", "noreply@kraivor.test")

DEBUG = True

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

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

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
