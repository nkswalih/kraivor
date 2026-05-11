from .base import *  # noqa: F401, F403, F405

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "kraivor",
        "USER": "kraivor",
        "PASSWORD": "kraivor",
        "HOST": "localhost",
        "PORT": "5433",
    }
}

EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False
EMAIL_USE_STARTTLS = False
EMAIL_FROM = "noreply@kraivor.local"

FRONTEND_URL = "http://localhost:3000"