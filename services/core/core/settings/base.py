from pathlib import Path

import environ

env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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
IDENTITY_JWKS_URL = env('IDENTITY_JWKS_URL', default='http://identity:8001/.well-known/jwks.json')
JWT_ALGORITHM = env('JWT_ALGORITHM', default='RS256')
JWT_AUDIENCE = env('JWT_AUDIENCE', default='kraivor')
JWT_ISSUER = env('JWT_ISSUER', default='kraivor-identity')
JWT_VERIFY_EXPIRATION = env.bool('JWT_VERIFY_EXPIRATION', default=True)

# Cache settings for JWKS
JWT_JWKS_CACHE_TTL = env.int('JWT_JWKS_CACHE_TTL', default=3600)

# Internal request header check
INTERNAL_REQUEST_HEADER = 'X-Internal-Request'