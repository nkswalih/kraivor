"""
authentication/oauth/google/services/verifier.py

Verifies a Google ID token using the google-auth library.

SECURITY CONTRACT:
  - Signature verified against Google's public certificates (fetched from JWKS)
  - aud claim MUST match GOOGLE_CLIENT_ID
  - iss claim MUST be accounts.google.com or https://accounts.google.com
  - exp claim MUST not be expired
  - email_verified MUST be True

We NEVER trust the raw token payload without signature verification.
The google-auth library handles certificate fetching, caching, and validation.
"""

from __future__ import annotations

import logging
from authentication.oauth.base import OAuthIdentityVerifier, OAuthUserInfo
from django.conf import settings
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

logger = logging.getLogger(__name__)

VALID_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})

# Singleton transport — reuses connection pool across requests
_transport = google_requests.Request()


class GoogleIDTokenVerificationError(Exception):
    """Raised when the Google ID token fails any validation check."""


class GoogleIDTokenVerifier(OAuthIdentityVerifier):
    """
    Verifies Google ID tokens using the official google-auth library.

    Uses google.oauth2.id_token.verify_oauth2_token which:
      1. Fetches Google's public JWKS (cached by the library)
      2. Verifies the RS256 signature
      3. Validates aud, iss, exp automatically

    We additionally validate email_verified after the library check.
    """

    def __init__(self) -> None:
        self._client_id: str = settings.GOOGLE_CLIENT_ID

    def verify(self, raw_token_response: dict) -> OAuthUserInfo:
        """
        Verify the ID token from a Google token response.

        Args:
            raw_token_response: The dict returned by GoogleTokenExchanger.exchange()
                                 Must contain the 'id_token' key.

        Returns:
            OAuthUserInfo with verified identity claims.

        Raises:
            GoogleIDTokenVerificationError: On any validation failure.
        """
        raw_id_token: str | None = raw_token_response.get("id_token")
        if not raw_id_token:
            raise GoogleIDTokenVerificationError("Missing id_token in token response")

        try:
            # verify_oauth2_token validates: signature, aud, iss, exp
            claims = google_id_token.verify_oauth2_token(
                id_token=raw_id_token, request=_transport, audience=self._client_id
            )
        except GoogleAuthError as exc:
            logger.warning("google_id_token_verification_failed: %s", exc)
            raise GoogleIDTokenVerificationError(
                f"ID token verification failed: {exc}"
            ) from exc
        except ValueError as exc:
            # google-auth raises ValueError for malformed tokens
            logger.warning("google_id_token_malformed: %s", exc)
            raise GoogleIDTokenVerificationError(f"Malformed ID token: {exc}") from exc

        # --- Additional validation not covered by google-auth ---

        # Validate issuer explicitly (defence-in-depth)
        iss = claims.get("iss", "")
        if iss not in VALID_ISSUERS:
            raise GoogleIDTokenVerificationError(f"Invalid issuer: {iss!r}")

        # Require verified email — users with unverified emails are untrusted
        if not claims.get("email_verified", False):
            raise GoogleIDTokenVerificationError("Google account email is not verified")

        # Require email to be present
        email = claims.get("email")
        if not email:
            raise GoogleIDTokenVerificationError("ID token missing email claim")

        # Require stable user identifier
        sub = claims.get("sub")
        if not sub:
            raise GoogleIDTokenVerificationError("ID token missing sub claim")

        return OAuthUserInfo(
            provider="google",
            provider_user_id=sub,
            email=email.lower(),
            name=claims.get("name", ""),
            avatar_url=claims.get("picture"),
            email_verified=True,
            raw=claims,
        )
