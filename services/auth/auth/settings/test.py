"""
Test settings — uses SQLite in-memory so tests run without a live Postgres.
Never use in production or staging.
"""

import os
from pathlib import Path

from .base import *  # noqa: F401, F403, F405

DEBUG = True

# Fast in-memory DB for tests — no Postgres required
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Silence password hashers for speed
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Email — no real sending in tests (views mock email_service anyway)
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
EMAIL_FROM = "test@kraivor.test"
FRONTEND_URL = "http://localhost:3000"

# KRV-012: JWT keys for tests - use temp directory
TEST_KEYS_DIR = Path(__file__).parent.parent.parent.parent / ".keys"
JWT_PUBLIC_KEY_PATH = str(TEST_KEYS_DIR / "jwt-public.pem")
JWT_PRIVATE_KEY_PATH = str(TEST_KEYS_DIR / "jwt-private.pem")
