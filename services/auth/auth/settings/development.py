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

from .base import *  # noqa: F401, F403, F405

# =============================================================================
# DEBUG MODE
# =============================================================================
# Enable debug mode for development
# WHY: Shows detailed error pages with full tracebacks
# NOTE: Never enable in production!
DEBUG = True

# =============================================================================
# ALLOWED HOSTS - Development
# =============================================================================
# Allow localhost variations for local development
# WHY: Django validates Host header to prevent cache poisoning
ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=[
        'localhost',
        '127.0.0.1',
        '127.0.0.1:3000',
        'localhost:3000',
        '127.0.0.1:8001',
        'localhost:8001',
    ]
)

# =============================================================================
# CORS - Development
# =============================================================================
# Allow all origins in development
# WHY: Frontend runs on different port during development
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=True)
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=True)

# =============================================================================
# DATABASE - Development (Local PostgreSQL)
# =============================================================================
# Can be overridden via DATABASE_URL in .env
# Default connects to Docker PostgreSQL on localhost:5433
# (Uses 5433 instead of 5432 to avoid conflicts with local PostgreSQL)

# =============================================================================
# EMAIL - Development (Mailhog)
# =============================================================================
# Mailhog is a local email testing server
# Web UI: http://localhost:8025
# SMTP: localhost:1025
# WHY: Allows testing emails without sending to real addresses

EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=1025)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_USE_STARTTLS = env.bool('EMAIL_USE_STARTTLS', default=False)
EMAIL_FROM = env('EMAIL_FROM', default='noreply@kraivor.local')

# =============================================================================
# FRONTEND URL - Development
# =============================================================================

FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')

# =============================================================================
# COOKIES - Development
# =============================================================================
# Cookies work over HTTP in development
# WHY: Browsers block secure cookies over HTTP
COOKIE_SECURE = env.bool('COOKIE_SECURE', default=False)
COOKIE_DOMAIN = env('COOKIE_DOMAIN', default='')
COOKIE_SAMESITE = env('COOKIE_SAMESITE', default='Lax')

# =============================================================================
# STATIC & MEDIA - Development
# =============================================================================
# Serve media files in development (Django's runserver)
# In production, use Nginx/WhiteNoise

# =============================================================================
# LOGGING - Development
# =============================================================================
# More verbose logging in development

import logging

LOGGING['root']['level'] = 'DEBUG'
LOGGING['loggers']['django']['level'] = 'DEBUG'

# =============================================================================
# PASSWORD VALIDATION - Development
# =============================================================================
# Relaxed validation for easier testing
# Remove in production!

# =============================================================================
# CACHES - Development
# =============================================================================
# Use local memory cache for faster development
# In production, use Redis

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# =============================================================================
# REST FRAMEWORK - Development
# =============================================================================

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',  # Nice HTML UI
]

# =============================================================================
# Celery - Development
# =============================================================================
# Run celery tasks synchronously in development
# Remove in production for async processing

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True