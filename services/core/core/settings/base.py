from pathlib import Path

import environ

env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent.parent

# Read .env file - central configuration for all environments
ROOT_ENV_FILE = PROJECT_ROOT / ".env"
if ROOT_ENV_FILE.exists():
    environ.Env.read_env(ROOT_ENV_FILE)

SECRET_KEY = env('SECRET_KEY', default='django-insecure-dummy-key-for-test-and-build')

DEBUG = env('DEBUG', default=False)

ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS', 
    default=[
        "localhost",
        "127.0.0.1",
        "core",
        "identity",
        "auth",
        "nginx",
        "analysis",
        "ai",
        "notifications",
    ])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'apps.workspaces',
    'apps.repositories',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.middleware.jwt_auth.JWTAuthenticationMiddleware',
]

ROOT_URLCONF = 'core.urls'

WSGI_APPLICATION = 'core.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
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

STATIC_URL = '/static/'

DATABASES = {
    'default': env.db_url('DATABASE_URL')
}

AUTH_PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# KRV-012: JWT Configuration
# JWKS endpoint URL - Identity Service

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "apps.workspaces.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

IDENTITY_JWKS_URL = env('IDENTITY_JWKS_URL', default='http://identity:8001/.well-known/jwks.json')
JWT_ALGORITHM = env('JWT_ALGORITHM', default='RS256')
JWT_AUDIENCE = env('JWT_AUDIENCE', default='kraivor')
JWT_ISSUER = env('JWT_ISSUER', default='kraivor-identity')
JWT_VERIFY_EXPIRATION = env.bool('JWT_VERIFY_EXPIRATION', default=True)

# Key ID used by Identity Service for JWT kid header
# Must match the kid in the identity service's JWKS endpoint
JWT_KEY_ID = env('JWT_KEY_ID', default='kraivor-rs256-dev-key')

# Cache settings for JWKS
JWT_JWKS_CACHE_TTL = env.int('JWT_JWKS_CACHE_TTL', default=3600)

# Internal request header check
INTERNAL_REQUEST_HEADER = 'X-Internal-Request'