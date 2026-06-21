# ruff: noqa: F401, F403, F405
from .base import *

DEBUG = True

REST_FRAMEWORK = {"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"]}

# Always use S3 (MinIO in dev, real S3 in prod). Ignore env var override.
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
STORAGES = {
    "default": {"BACKEND": DEFAULT_FILE_STORAGE},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
