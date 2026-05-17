"""
Django Base Settings - Production-Grade Configuration
========================================================

This file contains the core configuration that applies to ALL environments.
It uses django-environ for 12-factor app compliance, loading configuration
from environment variables with sensible defaults for development safety.

Key Design Principles:
1. Environment variables are the single source of truth
2. Secrets are NEVER hardcoded - always come from env
3. Sensible defaults provided ONLY for non-sensitive settings
4. Production will FAIL FAST if required secrets are missing
5. All settings are documented with WHY they exist

Project Structure Expected:
project/
├── .env                    # Local environment (NOT in git)
├── .env.example            # Template for contributors
├── services/
│   └── auth/
│       ├── .keys/          # Local JWT keys (NOT in git)
│       │   ├── jwt-private.pem
│       │   └── jwt-public.pem
│       ├── auth/
│       │   └── settings/
│       │       ├── base.py       # This file
│       │       ├── development.py
│       │       ├── production.py
│       │       └── staging.py
"""

import os
from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# =============================================================================
# ENVIRONMENT CONFIGURATION - 12-Factor App Principle
# =============================================================================
# django-environ handles loading from .env file and environment variables
# Priority: env vars > .env file > defaults
# This enables Docker/K8s secret injection in production

env = environ.Env(
    DEBUG=(bool, False)
)

# Build paths relative to the auth service root.
# services/auth/auth/settings/base.py -> services/auth
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent.parent

# Read .env file - this is the central configuration for all environments
# In production, env vars can override .env values (Docker/K8s secret injection)
ROOT_ENV_FILE = PROJECT_ROOT / ".env"

if ROOT_ENV_FILE.exists():
    environ.Env.read_env(ROOT_ENV_FILE)


def required_env(name: str) -> str:
    """Read a required environment variable with a clear deployment error."""
    try:
        return env(name)
    except ImproperlyConfigured as exc:
        raise ImproperlyConfigured(f"Set the {name} environment variable") from exc


def required_env_path(name: str) -> str:
    """
    Resolve a required path from env.

    Absolute paths are used as-is. Relative paths are resolved from the auth
    service root, with compatibility for repo-root paths such as
    services/auth/.keys/jwt-public.pem.
    """
    value = Path(required_env(name))
    if value.is_absolute():
        return str(value)

    if value.parts[:2] == ("services", "auth"):
        return str(PROJECT_ROOT / value)

    service_path = BASE_DIR / value
    project_path = PROJECT_ROOT / value
    if project_path.exists() and not service_path.exists():
        return str(project_path)

    return str(service_path)

# =============================================================================
# CORE SECURITY SETTINGS
# =============================================================================

# SECRET_KEY: Required for Django's cryptographic signing
# WHY: Used for session signing, CSRF tokens, password reset tokens, etc.
# PRODUCTION: MUST be unique, long, and NEVER committed to git
# Generates via: python -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY = required_env('SECRET_KEY')

# DEBUG: Controls detailed error pages and auto-reloading
# WHY: True shows full tracebacks (security risk in production)
# PRODUCTION: MUST be False - disable in production to prevent information leakage
DEBUG = env('DEBUG', default=False)

# ALLOWED_HOSTS: Valid host/domain names for this Django site
# WHY: Prevents HTTP Host header attacks (cache poisoning, SSRF)
# PRODUCTION: List your exact domain(s) - no wildcards unless behind CDN
# Microservices: Each service needs its own allowed hosts
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# =============================================================================
# APPLICATION CONFIGURATION
# =============================================================================

# INSTALLED_APPS: Django apps included in the project
# WHY: Controls which apps are loaded and their models/admin/views
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'users',
    'authentication',
    'api_keys',
]

# MIDDLEWARE: Request/response processing pipeline
# WHY: Chain of processors for every request - order matters!
# Security middleware placed early to catch issues first
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # CORS before security
    'django.middleware.security.SecurityMiddleware',  # Security headers
    'django.contrib.sessions.middleware.SessionMiddleware',  # Sessions
    'django.middleware.common.CommonMiddleware',  # Common utilities
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Auth
    'django.contrib.messages.middleware.MessageMiddleware',  # Messages
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Clickjacking
]

ROOT_URLCONF = 'auth.urls'
WSGI_APPLICATION = 'auth.wsgi.application'

# =============================================================================
# TEMPLATES CONFIGURATION
# =============================================================================

# Django template engine configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # Add template directories here if needed
        'APP_DIRS': True,  # Look in app templates/ directories
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# =============================================================================
# DATABASE CONFIGURATION - PostgreSQL
# =============================================================================
# PostgreSQL is required for production - provides:
# - ACID compliance for data integrity
# - Connection pooling
# - Full-text search
# - JSON support

DATABASES = {
    'default': env.db('DATABASE_URL')
}

# PASSWORD_HASHERS: How passwords are hashed
# WHY: Argon2 is the winner of the Password Hashing Competition
# PRODUCTION: Use Argon2, fallback to PBKDF2 (Django default)
# NOTE: Argon2 requires `pip install argon2-cffi`
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

# AUTH_USER_MODEL: Custom user model
# WHY: Allows extending user model without breaking relations
AUTH_USER_MODEL = 'users.User'

# =============================================================================
# CACHING CONFIGURATION - Redis
# =============================================================================
# Redis is required for production - provides:
# - Sub-millisecond latency
# - Pub/sub for Celery
# - Session storage
# - Rate limiting

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://localhost:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'kraivor',
        'TIMEOUT': 300,  # Default 5 minutes
    }
}

# Redis session backend
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# =============================================================================
# REDIS URL - Direct access for authentication services
# =============================================================================
# Centralized Redis URL for OTP, rate limiting, and login lockout
# Derived from CACHES location for consistency
REDIS_URL = CACHES['default']['LOCATION']

# =============================================================================
# AUTHENTICATION & JWT CONFIGURATION
# =============================================================================

# REST Framework JWT Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}

# Simple JWT (DJANGO REST FRAMEWORK SIMPLEJWT)
# WHY: Lightweight JWT implementation for stateless auth
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,  # Issue new refresh token on use
    'BLACKLIST_AFTER_ROTATION': True,  # Invalidate old refresh tokens
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# JWT (RS256) - Asymmetric Keys for API Security
# WHY: RS256 provides better security than HS256 (shared secret)
# Public key can be shared with other services (JWKS endpoint)
JWT_PRIVATE_KEY_PATH = required_env_path('JWT_PRIVATE_KEY_PATH')
JWT_PUBLIC_KEY_PATH = required_env_path('JWT_PUBLIC_KEY_PATH')
JWT_ALGORITHM = env('JWT_ALGORITHM', default='RS256')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = env.int('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', default=15)
JWT_REFRESH_TOKEN_EXPIRE_DAYS = env.int('JWT_REFRESH_TOKEN_EXPIRE_DAYS', default=30)

# =============================================================================
# CORS (Cross-Origin Resource Sharing) CONFIGURATION
# =============================================================================
# WHY: Controls which domains can access your API
# SECURITY: Be specific in production - never allow all origins

CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)
CORS_ALLOW_CREDENTIALS = env.bool('CORS_ALLOW_CREDENTIALS', default=True)

# Whitelist specific origins in production
# CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])

# =============================================================================
# SECURITY HEADERS
# =============================================================================

# Content Security Policy
SECURE_CONTENT_TYPE_NOSNIFF = env.bool('SECURE_CONTENT_TYPE_NOSNIFF', default=True)

# X-Frame-Options - Clickjacking protection
X_FRAME_OPTIONS = env('X_FRAME_OPTIONS', default='DENY')

# =============================================================================
# COOKIE CONFIGURATION
# =============================================================================
# WHY: Secure cookie settings prevent XSS theft and CSRF attacks

COOKIE_DOMAIN = env('COOKIE_DOMAIN', default='')
COOKIE_SECURE = env.bool('COOKIE_SECURE', default=False)  # HTTPS only in production
COOKIE_SAMESITE = env('COOKIE_SAMESITE', default='Lax')  # CSRF protection
COOKIE_PATH = env('COOKIE_PATH', default='/auth/')
COOKIE_HTTPONLY = env.bool('COOKIE_HTTPONLY', default=True)  # Prevent XSS access
COOKIE_SAMESITE_FORCE = env.bool('COOKIE_SAMESITE_FORCE', default=None)

# =============================================================================
# EMAIL / SMTP CONFIGURATION
# =============================================================================
# WHY: Transactional emails (password reset, verification, notifications)

FRONTEND_URL = required_env('FRONTEND_URL')

# SMTP Configuration
EMAIL_BACKEND = env('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = required_env('EMAIL_HOST')  # e.g., smtp.sendgrid.net, smtp.mailgun.org
EMAIL_PORT = env.int('EMAIL_PORT')  # 587 (TLS) or 465 (SSL)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS')
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
EMAIL_TIMEOUT = env.int('EMAIL_TIMEOUT', default=30)
EMAIL_FROM = required_env('EMAIL_FROM')  # noreply@yourdomain.com

# =============================================================================
# STATIC & MEDIA FILES
# =============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# WhiteNoise for serving static files in production (no external web server needed)
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Create logs directory if it doesn't exist
logs_dir = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "%(levelname)s", "time": "%(asctime)s", "module": "%(module)s", "message": "%(message)s"}',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(logs_dir, 'django.log'),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': env('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# =============================================================================
# LOGIN SECURITY - Rate Limiting & Lockout
# =============================================================================

# Redis-based login failure tracking
# WHY: Prevents brute force attacks on login endpoint
LOGIN_MAX_FAILURES = env.int('LOGIN_MAX_FAILURES', default=5)
LOGIN_LOCKOUT_MINUTES = env.int('LOGIN_LOCKOUT_MINUTES', default=15)
LOGIN_FAILURE_SIGNAL = 'authentication.signals.lockout_signal'

# =============================================================================
# OTP (One-Time Password) CONFIGURATION
# =============================================================================

OTP_CODE_LENGTH = 6
OTP_EXPIRE_MINUTES = 5
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_WAIT_SECONDS = 60

# =============================================================================
# INTERNAL SERVICE COMMUNICATION (Microservices)
# =============================================================================

# Header used for internal service-to-service communication
# WHY: Allows services to verify requests come from other trusted services
INTERNAL_REQUEST_HEADER = env('INTERNAL_REQUEST_HEADER', default='X-Internal-Request')
INTERNAL_REQUEST_TOKEN = env('INTERNAL_REQUEST_TOKEN', default='')

# =============================================================================
# ASYNC TASKS - Celery Configuration
# =============================================================================

# Celery broker and result backend
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/1')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/1')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes max

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# =============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# SECRET VALIDATION (Fail Fast)
# =============================================================================
# These checks run at startup to catch missing configuration early

if DEBUG is False and SECRET_KEY == 'dev-secret-key-not-for-production':
    raise ValueError(
        "SECRET_KEY must be set in production! "
        "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(50))\""
    )
