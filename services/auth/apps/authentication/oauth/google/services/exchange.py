"""
authentication/oauth/google/services/exchange.py

Exchanges a Google authorization code for an access token + ID token.

IMPORTANT SECURITY NOTE:
  We request the ID token here but NEVER trust the access token for identity.
  Identity is established ONLY from the verified ID token (see verifier.py).
"""

from __future__ import annotations

import logging

import requests
from authentication.oauth.base import OAuthTokenExchanger
from django.conf import settings

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


class GoogleTokenExchangeError(Exception):
    """Raised when the code→token exchange with Google fails."""


class GoogleTokenExchanger(OAuthTokenExchanger):
    """
    Exchanges authorization code for Google token response.

    The response contains:
      - access_token  (DO NOT use for identity — untrusted for auth)
      - id_token      (JWT — verify this in GoogleIDTokenVerifier)
      - token_type
      - expires_in
      - refresh_token (only on first grant / prompt=consent)
      - scope
    """

    def __init__(self) -> None:
        self._client_id: str = settings.GOOGLE_CLIENT_ID
        self._client_secret: str = settings.GOOGLE_CLIENT_SECRET
        self._redirect_uri: str = settings.GOOGLE_REDIRECT_URI

    def exchange(self, code: str) -> dict:
        """
        POST to Google token endpoint.

        Args:
            code: Authorization code from Google callback query param.

        Returns:
            Raw token response dict from Google.

        Raises:
            GoogleTokenExchangeError: On any HTTP or API error.
        """
        payload = {
            "code": code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
        }

        try:
            response = requests.post(
                GOOGLE_TOKEN_ENDPOINT,
                data=payload,
                timeout=10,
            )
        except requests.RequestException as exc:
            logger.error("google_token_exchange_network_error: %s", exc)
            raise GoogleTokenExchangeError(
                "Network error contacting Google token endpoint"
            ) from exc

        if not response.ok:
            # Log status but NOT the response body (may contain secrets)
            logger.error(
                "google_token_exchange_http_error: status=%s",
                response.status_code,
            )
            raise GoogleTokenExchangeError(
                f"Google token endpoint returned HTTP {response.status_code}"
            )

        data = response.json()

        if "error" in data:
            logger.error(
                "google_token_exchange_api_error: error=%s description=%s",
                data.get("error"),
                data.get("error_description", ""),
            )
            raise GoogleTokenExchangeError(
                f"Google API error: {data.get('error_description', data['error'])}"
            )

        if "id_token" not in data:
            raise GoogleTokenExchangeError("Google response missing id_token — cannot authenticate")

        return data
