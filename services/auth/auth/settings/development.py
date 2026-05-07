from .base import *  # noqa: F401, F403, F405

DEBUG = True

# Use localhost for local dev, can be overridden via DATABASE_URL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "kraivor_dev",
        "USER": "kraivor",
        "PASSWORD": "kraivor",
        "HOST": env("DB_HOST", default="localhost"),  # noqa: F405
        "PORT": "5432",
    }
}

# ---------------------------------------------------------------------------
# Email — MailHog (development only, KRV-010)
# MailHog captures all outbound email; view at http://localhost:8025
# ---------------------------------------------------------------------------
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False
EMAIL_USE_STARTTLS = False
EMAIL_FROM = "noreply@kraivor.local"

FRONTEND_URL = "http://localhost:3000"