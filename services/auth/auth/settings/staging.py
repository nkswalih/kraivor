# ruff: noqa: F401, F403, F405
"""
Django Staging Settings
========================

Staging environment configuration - mirrors production as closely as possible
to ensure reliable deployments. Staging is where you test production-ready code.

Staging vs Production Differences:
- Uses staging/development services (staging DB, staging Redis)
- DEBUG may be True or False (usually False for production parity)
- Allowed hosts include staging domain
- May allow some testing tools (like Sentry in non-error mode)
- Connection to production-like infrastructure

Staging Purpose:
1. Test deployment process
2. QA testing environment
3. Pre-production validation
4. Performance testing
5. Mirror production configuration

Environment Variables:
- All secrets should be different from production
- Database: staging PostgreSQL
- Cache: staging Redis
- Email: staging SMTP or mailhog
"""

from .base import *

# =============================================================================
# DEBUG MODE - STAGING
# =============================================================================
# False for production parity - catch issues early
DEBUG = env('DEBUG', default=False)

# =============================================================================
# ALLOWED HOSTS - STAGING
# =============================================================================
ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=[
        'staging.your-domain.com',
        'staging-api.your-domain.com',
    ]
)

# =============================================================================
# CORS - STAGING
# =============================================================================
# Allow staging frontend
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=True)

# =============================================================================
# SECURITY HEADERS - STAGING
# =============================================================================
# Similar to production but may have differences for testing

SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=60)  # Shorter for staging
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=False)

# =============================================================================
# COOKIES - STAGING
# =============================================================================
COOKIE_SECURE = env.bool('COOKIE_SECURE', default=True)
COOKIE_SAMESITE = env('COOKIE_SAMESITE', default='Lax')  # More lenient for testing
COOKIE_DOMAIN = env('COOKIE_DOMAIN', default='')

CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)

# =============================================================================
# PROXY TRUST - STAGING
# =============================================================================
SECURE_PROXY_SSL_HEADER = env.list(
    'SECURE_PROXY_SSL_HEADER',
    default=[('HTTP_X_FORWARDED_PROTO', 'https')]
)

# =============================================================================
# DATABASE - STAGING
# =============================================================================
# Uses staging database, not production

# =============================================================================
# CACHES - STAGING
# =============================================================================
# Use Redis but different database number than production

# =============================================================================
# LOGGING - STAGING
# =============================================================================
# Similar to production but may include more debug info

LOGGING['root']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'INFO'

# =============================================================================
# EMAIL - STAGING
# =============================================================================
# Use staging email service or Mailhog for testing

# =============================================================================
# CELERY - STAGING
# =============================================================================
# Async like production

CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

# =============================================================================
# STAGING-SPECIFIC FEATURES
# =============================================================================

# Enable debug toolbar in staging (optional)
# if DEBUG:
#     INSTALLED_APPS += ['debug_toolbar']
#     MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

# Maintenance mode (optional)
# MAINTENANCE_MODE = env.bool('MAINTENANCE_MODE', default=False)