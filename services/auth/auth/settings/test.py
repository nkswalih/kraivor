"""
Django Test Settings
=====================

Configuration optimized for running tests.
Uses SQLite in-memory for speed and isolation.
No external services required.

Key Features:
- In-memory SQLite (no PostgreSQL needed)
- Fast password hashers
- Mock email backend (doesn't send)
- Test JWT keys
- Memory cache for speed

Usage:
    DJANGO_SETTINGS_MODULE=auth.settings.test pytest
    python manage.py test --settings=auth.settings.test
"""

import os
from pathlib import Path

from .base import *  # noqa: F401, F403, F405

# =============================================================================
# DEBUG MODE - TEST
# =============================================================================
DEBUG = True

# =============================================================================
# DATABASE - TEST (SQLite in-memory)
# =============================================================================
# Fast, no setup required, isolated per test run
# WHY: Avoids PostgreSQL overhead for unit tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# =============================================================================
# PASSWORD HASHERS - TEST
# =============================================================================
# Use fast hasher for quick tests
# WHY: MD5 is much faster than Argon2/PBKDF2 (testing only!)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# =============================================================================
# CACHES - TEST
# =============================================================================
# Memory cache is fastest for testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# =============================================================================
# EMAIL - TEST
# =============================================================================
# Use in-memory email backend (captures emails for inspection)
# WHY: No real emails sent during tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025
EMAIL_FROM = 'test@kraivor.test'
FRONTEND_URL = 'http://localhost:3000'

# =============================================================================
# JWT KEYS - TEST
# =============================================================================
# Use test keys from .keys directory
TEST_KEYS_DIR = Path(__file__).parent.parent.parent.parent / '.keys'
JWT_PUBLIC_KEY_PATH = str(TEST_KEYS_DIR / 'jwt-public.pem')
JWT_PRIVATE_KEY_PATH = str(TEST_KEYS_DIR / 'jwt-private.pem')

# =============================================================================
# REST FRAMEWORK - TEST
# =============================================================================
# Simpler authentication for tests
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'rest_framework.authentication.SessionAuthentication',
    'rest_framework_simplejwt.authentication.JWTAuthentication',
]

REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.IsAuthenticated',
]

# =============================================================================
# CORS - TEST
# =============================================================================
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# ALLOWED HOSTS - TEST
# =============================================================================
ALLOWED_HOSTS = ['*']

# =============================================================================
# LOGGING - TEST
# =============================================================================
# Reduce noise during tests
import logging

LOGGING['root']['level'] = 'CRITICAL'
LOGGING['loggers']['django']['level'] = 'CRITICAL'

# =============================================================================
# CELERY - TEST
# =============================================================================
# Run tasks synchronously in tests
# WHY: Avoid async complexity in unit tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# =============================================================================
# SECRET KEY - TEST (Fixed for reproducibility)
# =============================================================================
# Use fixed key for test reproducibility
SECRET_KEY = 'test-secret-key-for-testing-only-not-for-production'

# =============================================================================
# DISABLE MIGRATIONS IN TESTS (Optional, for speed)
# =============================================================================
# Uncomment to use in-memory models (faster but less accurate):
#
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __iter__(self):
#         return iter([])
#
# MIGRATION_MODULES = DisableMigrations()