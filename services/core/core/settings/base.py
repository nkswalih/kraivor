from pathlib import Path

import environ

env = environ.Env(DEBUG=(bool, False))

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent.parent

# Read .env file - central configuration for all environments
ROOT_ENV_FILE = PROJECT_ROOT / ".env"
if ROOT_ENV_FILE.exists():
    environ.Env.read_env(ROOT_ENV_FILE)

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dummy-key-for-test-and-build")

DEBUG = env("DEBUG", default=False)

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
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
    ],
)

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "channels",
    "apps.workspaces",
    "apps.repositories",
    "apps.knowledge",
    "apps.chat",
    "apps.notifications",
    "apps.projects",
    "apps.community",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "core.middleware.jwt_auth.JWTAuthenticationMiddleware",
]

ROOT_URLCONF = "core.urls"

WSGI_APPLICATION = "core.wsgi.application"

ASGI_APPLICATION = "core.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DATABASES = {"default": env.db_url("DATABASE_URL")}

AUTH_PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# KRV-012: JWT Configuration
# JWKS endpoint URL - Identity Service

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["apps.workspaces.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

IDENTITY_JWKS_URL = env(
    "IDENTITY_JWKS_URL", default="http://identity:8001/.well-known/jwks.json"
)
JWT_ALGORITHM = env("JWT_ALGORITHM", default="RS256")
JWT_AUDIENCE = env("JWT_AUDIENCE", default="kraivor")
JWT_ISSUER = env("JWT_ISSUER", default="kraivor-identity")
JWT_VERIFY_EXPIRATION = env.bool("JWT_VERIFY_EXPIRATION", default=True)

# Key ID used by Identity Service for JWT kid header
# Must match the kid in the identity service's JWKS endpoint
JWT_KEY_ID = env("JWT_KEY_ID", default="kraivor-rs256-dev-key")

# Cache settings for JWKS
JWT_JWKS_CACHE_TTL = env.int("JWT_JWKS_CACHE_TTL", default=3600)

# =============================================================================
# Github
# =============================================================================

GITHUB_CLIENT_ID = env("GITHUB_CLIENT_ID", default="")
GITHUB_CONNECT_REDIRECT_URI = env("GITHUB_CONNECT_REDIRECT_URI", default="")

# =============================================================================
# GitHub App (Repository Access)
# =============================================================================

GITHUB_APP_ID = env("GITHUB_APP_ID", default="")
GITHUB_APP_SLUG = env("GITHUB_APP_SLUG", default="")
GITHUB_APP_CLIENT_ID = env("GITHUB_APP_CLIENT_ID", default="")
GITHUB_APP_PRIVATE_KEY = env("GITHUB_APP_PRIVATE_KEY", default="")
# Support file path instead of inline PEM content
if GITHUB_APP_PRIVATE_KEY and not GITHUB_APP_PRIVATE_KEY.strip().startswith("-----"):
    key_path = Path(GITHUB_APP_PRIVATE_KEY)
    if not key_path.is_absolute():
        for base in (PROJECT_ROOT, BASE_DIR):
            candidate = base / key_path
            if candidate.exists():
                key_path = candidate
                break
    if key_path.exists():
        GITHUB_APP_PRIVATE_KEY = key_path.read_text()
GITHUB_APP_CALLBACK_URL = env(
    "GITHUB_APP_CALLBACK_URL", default="http://localhost:8002/api/github-app/callback/"
)
GITHUB_APP_WEBHOOK_SECRET = env("GITHUB_APP_WEBHOOK_SECRET", default="")

# =============================================================================
# Frontend URL (for post-installation redirect)
# =============================================================================

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost")

# =============================================================================
# Channels / Daphne — WebSocket & Real-Time
# =============================================================================

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL", default="redis://localhost:6379/0")],
            "capacity": 1500,
            "expiry": 60,
        },
    }
}

# =============================================================================
# Celery — Async Task Queue
# =============================================================================

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ROUTES = {
    "workspaces.tasks.*": {"queue": "notifications"},
    "notifications.tasks.*": {"queue": "notifications"},
    "chat.tasks.*": {"queue": "default"},
}
CELERY_BEAT_SCHEDULE = {
    "cleanup_expired_notifications": {
        "task": "notifications.tasks.cleanup_expired_notifications",
        "schedule": 3600.0,
        "options": {"queue": "default"},
    },
    "sweep_stale_presence": {
        "task": "notifications.tasks.sweep_stale_presence",
        "schedule": 300.0,
        "options": {"queue": "default"},
    },
    "check-overdue-tasks": {
        "task": "projects.check_overdue_tasks",
        "schedule": 3600.0,
        "options": {"queue": "default"},
    },
}

# =============================================================================
# Kafka — Event Bus
# =============================================================================

KAFKA_BOOTSTRAP_SERVERS = env("KAFKA_BOOTSTRAP_SERVERS", default="localhost:9092")
KAFKA_FLUSH_TIMEOUT = env.float("KAFKA_FLUSH_TIMEOUT", default=2.0)
KAFKA_CONSUMER_GROUP = env("KAFKA_CONSUMER_GROUP", default="core-consumer")
KAFKA_AUTO_CREATE_TOPICS = env.bool("KAFKA_AUTO_CREATE_TOPICS", default=True)

# =============================================================================
# DynamoDB — Chat Message Storage
# =============================================================================

DYNAMODB_LOCAL = env.bool("DYNAMODB_LOCAL", default=False)
DYNAMODB_ENDPOINT = env("DYNAMODB_ENDPOINT", default="http://localhost:8000")
DYNAMODB_CHAT_TABLE = env("DYNAMODB_CHAT_TABLE", default="kraivor-chat-messages")
AWS_REGION = env("AWS_REGION", default="us-east-1")

# =============================================================================
# Redis — General purpose
# =============================================================================

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

# =============================================================================
# AWS Lambda — Notification dispatch (email / Slack / SMS)
# =============================================================================

AWS_LAMBDA_NOTIFICATION_FN = env("AWS_LAMBDA_NOTIFICATION_FN", default="")

# =============================================================================
# Firebase — Push Notifications (optional)
# =============================================================================

FIREBASE_CREDENTIALS_PATH = env("FIREBASE_CREDENTIALS_PATH", default=None)

# Internal request header check
INTERNAL_REQUEST_HEADER = "X-Internal-Request"
