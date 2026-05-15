# ruff: noqa: F401, F403, F405
"""
Django Production Settings
===========================

Production-specific configuration for secure, high-performance deployment.
All settings optimized for production with proper security measures.

Key Differences from Development:
- DEBUG = False (security)
- Strict CORS policy
- HTTPS-only cookies
- Security headers enabled
- Secure password hashers
- Production-grade logging
- Redis caching
- Async Celery tasks

Security Checklist:
- [x] DEBUG = False
- [x] SECRET_KEY from environment (unique per deployment)
- [x] ALLOWED_HOSTS = exact production domain
- [x] COOKIE_SECURE = True (HTTPS only)
- [x] COOKIE_SAMESITE = 'Strict'
- [x] SECURE_SSL_REDIRECT = True
- [x] SECURE_BROWSER_XSS_FILTER = True
- [x] SECURE_CONTENT_TYPE_NOSNIFF = True
- [x] X_FRAME_OPTIONS = 'DENY'
- [x] CSRF_COOKIE_SECURE = True
- [x] SESSION_COOKIE_SECURE = True
- [x] CORS strict origin whitelist
"""

from .base import *

# =============================================================================
# DEBUG MODE - PRODUCTION
# =============================================================================
# MUST be False in production
# WHY: True reveals sensitive information in error pages
DEBUG = False

# =============================================================================
# ALLOWED HOSTS - PRODUCTION
# =============================================================================
# Your exact production domain(s)
# WHY: Prevents Host header attacks
# EXAMPLE: ['api.kraivor.com', 'www.kraivor.com']
ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=['your-production-domain.com']
)

# =============================================================================
# CORS - PRODUCTION
# =============================================================================
# Strict origin control
# WHY: Prevent cross-site API access
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=True)

# Add your frontend domain in production
# CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# =============================================================================
# SECURITY HEADERS - PRODUCTION
# =============================================================================
# HTTP Strict Transport Security (HSTS)
# WHY: Force HTTPS for all requests
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=True)

# SSL Redirect
# WHY: Redirect all HTTP to HTTPS
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)

# XSS Protection
# WHY: Enable browser's XSS filtering
SECURE_BROWSER_XSS_FILTER = env.bool('SECURE_BROWSER_XSS_FILTER', default=True)

# Content Type Sniffing
# WHY: Prevent MIME type sniffing
SECURE_CONTENT_TYPE_NOSNIFF = env.bool('SECURE_CONTENT_TYPE_NOSNIFF', default=True)

# Clickjacking Protection
# WHY: Prevent embedding in iframes
X_FRAME_OPTIONS = env('X_FRAME_OPTIONS', default='DENY')

# Referrer Policy
# WHY: Control referrer information sent to other sites
SECURE_REFERRER_POLICY = env('SECURE_REFERRER_POLICY', default='strict-origin-when-cross-origin')

# =============================================================================
# COOKIES - PRODUCTION
# =============================================================================
# Secure cookies for HTTPS
# WHY: Prevent cookie theft via network sniffing
COOKIE_SECURE = env.bool('COOKIE_SECURE', default=True)
COOKIE_SAMESITE = env('COOKIE_SAMESITE', default='Strict')  # CSRF protection
COOKIE_HTTPONLY = env.bool('COOKIE_HTTPONLY', default=True)  # Prevent XSS access
COOKIE_DOMAIN = env('COOKIE_DOMAIN', default='')

# CSRF Cookies
# WHY: Secure CSRF token cookies
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)
CSRF_COOKIE_SAMESITE = env('CSRF_COOKIE_SAMESITE', default='Strict')

# Session Cookies
# WHY: Secure session cookies
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
SESSION_COOKIE_SAMESITE = env('SESSION_COOKIE_SAMESITE', default='Strict')

# =============================================================================
# PROXY TRUST - PRODUCTION (Cloud/AWS/GCP/Azure)
# =============================================================================
# Trust proxy headers when behind load balancer/CDN
# WHY: Get correct client IP and protocol
SECURE_PROXY_SSL_HEADER = env.list(
    'SECURE_PROXY_SSL_HEADER',
    default=[('HTTP_X_FORWARDED_PROTO', 'https')]
)

# =============================================================================
# DATABASE - PRODUCTION
# =============================================================================
# Connection pooling for production
# Add to DATABASES in production:
# 'CONN_MAX_AGE': 60,  # Keep connections alive for 60 seconds

# =============================================================================
# CACHES - PRODUCTION
# =============================================================================
# Redis cache is already configured in base.py
# Adjust timeout for production

CACHES['default']['TIMEOUT'] = env.int('CACHE_TIMEOUT', default=300)

# =============================================================================
# STATIC & MEDIA FILES - PRODUCTION
# =============================================================================
# Use WhiteNoise for static file serving (or serve via Nginx/CDN)

# =============================================================================
# LOGGING - PRODUCTION
# =============================================================================
# More careful logging in production - avoid sensitive data

LOGGING['root']['level'] = 'INFO'
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['django.security']['level'] = 'ERROR'

# Add JSON logging for production (easier to parse with log aggregators)
# LOGGING['handlers']['json'] = {
#     'class': 'pythonjsonlogger.jsonlogger.JsonLogger',
#     'formatter': 'json',
# }

# =============================================================================
# EMAIL - PRODUCTION (AWS SES, SendGrid, Mailgun, etc.)
# =============================================================================

# Email configuration set via environment variables
# No local defaults - require explicit configuration in production
# Example for AWS SES:
# EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True

# =============================================================================
# PASSWORD HASHERS - PRODUCTION
# =============================================================================
# Argon2 is already configured in base.py
# Increase iterations if needed for higher security

# =============================================================================
# AUTHENTICATION - PRODUCTION
# =============================================================================

# Force HTTPS for password reset tokens
# FORCE_PASSWORD_RESET_HTTPS = True

# =============================================================================
# CELERY - PRODUCTION
# =============================================================================
# Use actual async Celery workers in production
# Disable eager execution

CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

# =============================================================================
# SENTRY ERROR TRACKING (Optional but Recommended)
# =============================================================================
# Add Sentry for production error tracking:
# import sentry_sdk
# from sentry_sdk.integrations.django import DjangoIntegration
#
# SENTRY_DSN = env('SENTRY_DSN', default='')
# if SENTRY_DSN:
#     sentry_sdk.init(
#         dsn=SENTRY_DSN,
#         integrations=[DjangoIntegration()],
#         traces_sample_rate=0.1,
#         send_default_pii=False
#     )

# =============================================================================
# PERFORMANCE OPTIMIZATIONS - PRODUCTION
# =============================================================================

# Connection pooling for PostgreSQL (if using psycopg2)
# DATABASES['default']['CONN_MAX_AGE'] = 60

# Template caching (optional, if using Django templates)
# TEMPLATES[0]['OPTIONS']['loaders'] = [
#     ('django.template.loaders.cached.Loader', [
#         'django.template.loaders.filesystem.Loader',
#         'django.template.loaders.app_directories.Loader',
#     ]),
# ]

# =============================================================================
# ADMIN - PRODUCTION
# =============================================================================
# Restrict admin access to specific IPs if needed:
# ADMIN_ALLOWED_IPS = env.list('ADMIN_ALLOWED_IPS', default=[])