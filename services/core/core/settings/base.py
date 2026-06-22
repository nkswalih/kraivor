from pathlib import Path

import environ
import mimetypes

mimetypes.add_type("text/markdown", ".md", strict=True)
mimetypes.add_type("text/markdown", ".mdx", strict=True)
mimetypes.add_type("text/yaml", ".yaml", strict=True)
mimetypes.add_type("text/yaml", ".yml", strict=True)
mimetypes.add_type("application/toml", ".toml", strict=True)

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
    "storages",
    "apps.workspaces",
    "apps.repositories",
    "apps.knowledge",
    "apps.chat",
    "apps.notifications",
    "apps.projects",
    "apps.community",
    "apps.search",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "core.middleware.csrf_exempt_api.CsrfExemptApiMiddleware",
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

# =============================================================================
# File Storage — S3 via MinIO (Development) or real S3 (Production)
# =============================================================================
# Defaults to S3. Set DEFAULT_FILE_STORAGE env var to switch back to
# FileSystemStorage if needed (e.g., for local testing without Docker).

DEFAULT_FILE_STORAGE = env(
    "DEFAULT_FILE_STORAGE",
    default="storages.backends.s3boto3.S3Boto3Storage",
)

STORAGES = {
    "default": {"BACKEND": DEFAULT_FILE_STORAGE},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_S3_ACCESS_KEY_ID = env("AWS_S3_ACCESS_KEY_ID", default="") or None
AWS_S3_SECRET_ACCESS_KEY = env("AWS_S3_SECRET_ACCESS_KEY", default="") or None
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default="")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="") or None
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
}
AWS_DEFAULT_ACL = "public-read"
AWS_QUERYSTRING_AUTH = False

DATABASES = {"default": env.db_url("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=300)

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
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "EXCEPTION_HANDLER": "core.exceptions.core_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
    "DEFAULT_VERSIONING_CLASS": None,
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
# Identity Service
# =============================================================================
IDENTITY_SERVICE_URL = env("IDENTITY_SERVICE_URL", default="http://identity:8002/api")

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
# Redis Cache
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "PARSER_CLASS": "redis.connection.DefaultParser",
            "IGNORE_EXCEPTIONS": True,
            "PICKLE_VERSION": -1,
        },
        "KEY_PREFIX": "kraivor",
        "TIMEOUT": 300,
    },
    "local": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "kraivor-local",
        "TIMEOUT": 60,
    },
}

# =============================================================================
# Sentry — Error Tracking & Performance Monitoring (optional)
# =============================================================================

SENTRY_DSN = env("SENTRY_DSN", default="")

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,
    )

# =============================================================================
# Structured Logging
# =============================================================================

try:
    import pythonjsonlogger  # noqa: F401

    _json_formatter = "pythonjsonlogger.jsonlogger.JsonFormatter"
except ImportError:
    _json_formatter = "logging.Formatter"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": _json_formatter,
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s %(module)s %(lineno)d",
        },
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s:%(lineno)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if not DEBUG else "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

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
