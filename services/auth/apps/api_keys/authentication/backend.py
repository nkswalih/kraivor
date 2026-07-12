"""
apps/api_keys/authentication/backend.py

DRF Authentication backend for Kraivor API keys.

Sits alongside the existing JWT backend in DEFAULT_AUTHENTICATION_CLASSES.
DRF tries each backend in order; this one owns any 'Bearer krv_live_…'
token and returns None immediately for all other token formats so the JWT
backend can handle them unimpeded.

request.user  → the User instance (same as JWT auth)
request.auth  → the APIKey instance (use for scope checking in permissions)
"""

from __future__ import annotations

import logging

from api_keys.services.generator import is_api_key_format
from api_keys.services.key_service import (
    APIKeyExpiredError,
    APIKeyNotFoundError,
    authenticate_api_key,
)
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class APIKeyAuthentication(BaseAuthentication):
    """
    DRF authentication class for Kraivor API keys.

    Register in settings:

        REST_FRAMEWORK = {
            "DEFAULT_AUTHENTICATION_CLASSES": [
                "api_keys.authentication.backend.APIKeyAuthentication",
                "rest_framework_simplejwt.authentication.JWTAuthentication",
            ],
        }
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        raw_token = parts[1]

        # Fast prefix check — if it's not a Kraivor key, let JWT backend try
        if not is_api_key_format(raw_token):
            return None

        # From here: this IS an API key token.  Any failure must raise.
        try:
            api_key = authenticate_api_key(raw_token)
        except APIKeyNotFoundError as err:
            raise AuthenticationFailed("Invalid API key.") from err

        except APIKeyExpiredError as err:
            raise AuthenticationFailed("API key has expired.") from err

        except Exception as err:
            logger.exception("api_key_authentication_unexpected_error")

            raise AuthenticationFailed("Authentication error.") from err

        return (api_key.user, api_key)

    def authenticate_header(self, request):
        return 'Bearer realm="api", error="invalid_token"'
