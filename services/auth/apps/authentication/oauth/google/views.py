"""
authentication/oauth/google/views.py

Two thin views that orchestrate the Google OAuth flow.

GET /auth/oauth/google/
  → Generates CSRF state, stores in Redis, redirects to Google consent screen.

GET /auth/oauth/google/callback/
  → Validates state, exchanges code, verifies ID token, creates/finds user,
    issues Kraivor JWT pair, returns auth response.

Views are intentionally thin — all business logic lives in services/.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from authentication.cookie_utils import create_refresh_cookie
from authentication.oauth.google.services.exchange import (
    GoogleTokenExchangeError,
    GoogleTokenExchanger,
)
from authentication.oauth.google.services.identity import GoogleIdentityService
from authentication.oauth.google.services.state import GoogleStateService
from authentication.oauth.google.services.verifier import (
    GoogleIDTokenVerificationError,
    GoogleIDTokenVerifier,
)
from authentication.security import get_client_ip
from authentication.tokens import get_token_service
from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"

# OpenID Connect scopes — openid is required for ID token
GOOGLE_SCOPES = "openid email profile"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    """Reuse the project-wide cookie utility."""
    cookie = create_refresh_cookie(raw_token)
    response.set_cookie(
        "refresh_token",
        cookie["value"],
        httponly=cookie["httponly"],
        secure=cookie["secure"],
        samesite=cookie["samesite"],
        path=cookie["path"],
        max_age=cookie["max_age"],
        domain=cookie.get("domain"),
    )


class GoogleOAuthInitiateView(APIView):
    """
    GET /auth/oauth/google/

    Initiates the Google OAuth 2.0 / OIDC flow:
      1. Generates a cryptographically random CSRF state token
      2. Stores the state in Redis (TTL = OAUTH_STATE_EXPIRE_SECONDS)
      3. Redirects the browser to Google's authorization endpoint

    No authentication required — this is the entry point.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> HttpResponseRedirect:
        state_service = GoogleStateService()

        try:
            state = state_service.generate()
        except RuntimeError:
            return Response(
                {"error": "Unable to initiate OAuth flow. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        params = urlencode(
            {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "response_type": "code",
                "scope": GOOGLE_SCOPES,
                "state": state,
                "access_type": "offline",  # request refresh_token
                "prompt": "select_account",
            }
        )

        redirect_url = f"{GOOGLE_AUTH_ENDPOINT}?{params}"
        return HttpResponseRedirect(redirect_url)


class GoogleOAuthCallbackView(APIView):
    """
    GET /auth/oauth/google/callback/

    Completes the Google OAuth flow:
      1. Validates CSRF state (atomic consume from Redis)
      2. Checks for OAuth error param
      3. Exchanges authorization code for Google tokens
      4. Verifies ID token (signature, aud, iss, exp, email_verified)
      5. Creates or finds Kraivor User + OAuthIdentity
      6. Issues Kraivor JWT access + refresh token pair
      7. Returns JSON auth response with refresh token in HttpOnly cookie

    All failures return structured JSON (no redirects on error — the
    frontend handles redirect logic based on the JSON response).
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        ip = get_client_ip(request)

        # ── 1. Extract query parameters ──────────────────────────────────────
        state = request.query_params.get("state", "")
        code = request.query_params.get("code", "")
        error = request.query_params.get("error", "")

        # ── 2. Handle user-denied / OAuth errors ─────────────────────────────
        if error:
            logger.info("google_oauth_user_denied: ip=%s error=%s", ip, error)
            return Response(
                {"error": "Google OAuth was denied or cancelled.", "error_code": "oauth_denied"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── 3. Validate CSRF state ────────────────────────────────────────────
        if not state:
            return Response(
                {"error": "Missing OAuth state parameter.", "error_code": "missing_state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        state_service = GoogleStateService()
        if not state_service.consume(state):
            logger.warning("google_oauth_invalid_state: ip=%s", ip)
            return Response(
                {"error": "Invalid or expired OAuth state.", "error_code": "invalid_state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── 4. Require authorization code ─────────────────────────────────────
        if not code:
            return Response(
                {"error": "Missing authorization code.", "error_code": "missing_code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── 5. Exchange code for Google tokens ────────────────────────────────
        exchanger = GoogleTokenExchanger()
        try:
            raw_tokens = exchanger.exchange(code)
        except GoogleTokenExchangeError as exc:
            logger.error("google_oauth_exchange_failed: ip=%s error=%s", ip, exc)
            return Response(
                {
                    "error": "Failed to exchange authorization code.",
                    "error_code": "exchange_failed",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ── 6. Verify Google ID token ─────────────────────────────────────────
        verifier = GoogleIDTokenVerifier()
        try:
            user_info = verifier.verify(raw_tokens)
        except GoogleIDTokenVerificationError as exc:
            logger.warning("google_oauth_id_token_invalid: ip=%s error=%s", ip, exc)
            return Response(
                {"error": "Google identity verification failed.", "error_code": "invalid_id_token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ── 7. Create or find Kraivor user ────────────────────────────────────
        identity_service = GoogleIdentityService()
        try:
            user, created = identity_service.get_or_create(user_info, raw_tokens)
        except Exception:
            logger.exception("google_oauth_identity_error: ip=%s email=%s", ip, user_info.email)
            return Response(
                {"error": "Failed to process account.", "error_code": "identity_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── 8. Issue Kraivor JWT pair ─────────────────────────────────────────
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        token_service = get_token_service()

        # Use a stable device_id derived from the Google sub claim
        # This lets the same Google account map to a consistent device record
        device_id = f"google:{user_info.provider_user_id}"

        try:
            tokens = token_service.generate_tokens(user, device_id, ip, user_agent)
        except Exception:
            logger.exception("google_oauth_token_issue_failed: user_id=%s", user.id)
            return Response(
                {"error": "Failed to issue session tokens.", "error_code": "token_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "google_oauth_login_success: user_id=%s email=%s new_user=%s",
            user.id,
            user_info.email,
            created,
        )

        # ── 9. Return auth response ───────────────────────────────────────────
        frontend_url = (
            f"{settings.FRONTEND_URL}/oauth/success"
            f"?access_token={tokens.access_token}"
        )

        response = HttpResponseRedirect(frontend_url)

        _set_refresh_cookie(response, tokens.refresh_token)

        return response
