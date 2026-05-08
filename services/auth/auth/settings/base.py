import os
from datetime import timedelta
from pathlib import Path

import environ

env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='dev-secret-key-not-for-production')

DEBUG = env('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

# Apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'apps.users.apps.UsersConfig',
    'apps.authentication.apps.AuthenticationConfig',
    'apps.api_keys.apps.ApiKeysConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'auth.urls'

WSGI_APPLICATION = 'auth.wsgi.application'

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

# Database
DATABASES = {
    'default': env.db_url('DATABASE_URL', default='postgresql://kraivor:kraivor@postgres:5432/kraivor_dev')
}

# Password hashers - Argon2 first as requested
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

# Custom user model
AUTH_USER_MODEL = 'users.User'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# CORS
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=True)

# Redis
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

# JWT (Simple JWT)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# ---------------------------------------------------------------------------
# Email (KRV-010)
# Override in development.py → MailHog, production.py → AWS SES SMTP
# ---------------------------------------------------------------------------
FRONTEND_URL = env('FRONTEND_URL', default='http://localhost:3000')

EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env.int('EMAIL_PORT', default=1025)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_USE_STARTTLS = env.bool('EMAIL_USE_STARTTLS', default=False)
EMAIL_FROM = env('EMAIL_FROM', default='noreply@kraivor.com')

# ---------------------------------------------------------------------------
# JWT (RS256) - KRV-011
# ---------------------------------------------------------------------------
JWT_PRIVATE_KEY_PATH = os.path.join(BASE_DIR, env('JWT_PRIVATE_KEY_PATH', default='.keys/jwt-private.pem'))
JWT_PUBLIC_KEY_PATH = os.path.join(BASE_DIR, env('JWT_PUBLIC_KEY_PATH', default='.keys/jwt-public.pem'))
JWT_ALGORITHM = env('JWT_ALGORITHM', default='RS256')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = env.int('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', default=15)
JWT_REFRESH_TOKEN_EXPIRE_DAYS = env.int('JWT_REFRESH_TOKEN_EXPIRE_DAYS', default=30)

# ---------------------------------------------------------------------------
# Login Lockout (Redis) - KRV-011
# ---------------------------------------------------------------------------
LOGIN_MAX_FAILURES = env.int('LOGIN_MAX_FAILURES', default=5)
LOGIN_LOCKOUT_MINUTES = env.int('LOGIN_LOCKOUT_MINUTES', default=15)

# ---------------------------------------------------------------------------
# OTP Configuration - KRV-011
# ---------------------------------------------------------------------------
OTP_CODE_LENGTH = 6
OTP_EXPIRE_MINUTES = 5
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_WAIT_SECONDS = 60