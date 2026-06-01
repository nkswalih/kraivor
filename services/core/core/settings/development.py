# ruff: noqa: F401, F403, F405
from .base import *

DEBUG = True

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}