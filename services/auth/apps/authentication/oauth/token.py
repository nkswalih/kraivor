"""
GitHub OAuth token retrieval endpoint — service-to-service only.

Internal endpoint called by the Core Service to retrieve a user's stored
GitHub OAuth access token. This avoids the Core Service needing direct
database access to the auth service's OAuthIdentity table.

Security:
  - Requires X-Internal-Request: 1 header (bypasses JWT verification)
  - Requires X-User-ID header (identifies the target user)
  - Not exposed to external clients — only reachable within Docker network
"""

import logging
from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import OAuthIdentity
from .encryption import get_encryption_service

logger = logging.getLogger(__name__)


class GitHubOAuthTokenView(APIView):
    """
    GET /api/oauth/github/token/

    Internal endpoint. Returns the user's stored GitHub OAuth access token.

    Headers:
      X-Internal-Request: 1    — required, bypasses JWT auth
      X-User-ID: <uuid>        — required, the user whose token to retrieve

    Responses:
      200  {"access_token": "<github_pat>"}
      400  Missing required headers
      404  User has no connected GitHub account
      500  Token decryption failed / unexpected error
    """

    permission_classes = []  # Authenticated via headers, not JWT

    def get(self, request: Request) -> Response:
        # ── Verify internal request header ──────────────────────────────────
        internal_header = getattr(settings, "INTERNAL_REQUEST_HEADER", "X-Internal-Request")
        if request.headers.get(internal_header) != "1":
            logger.warning("github.token.missing_internal_header")
            return Response(
                {"error": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Extract user ID ─────────────────────────────────────────────────
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            return Response(
                {"error": "Missing X-User-ID header"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Fetch OAuth identity ────────────────────────────────────────────
        try:
            oauth_identity = OAuthIdentity.objects.get(
                user_id=user_id,
                provider="github",
                deleted_at__isnull=True,
            )
        except OAuthIdentity.DoesNotExist:
            logger.info(
                "github.token.not_found",
                extra={"user_id": user_id},
            )
            return Response(
                {"error": "No GitHub account connected"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Decrypt token ────────────────────────────────────────────────────
        encrypted_token = oauth_identity.access_token_encrypted
        if not encrypted_token:
            logger.error(
                "github.token.missing_encrypted",
                extra={"user_id": user_id, "oauth_id": str(oauth_identity.id)},
            )
            return Response(
                {"error": "No stored token for this GitHub account"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            encryption_service = get_encryption_service()
            token = encryption_service.decrypt(encrypted_token)
        except Exception as exc:
            logger.error(
                "github.token.decryption_failed",
                extra={"user_id": user_id, "error": str(exc)},
            )
            return Response(
                {"error": "Failed to retrieve GitHub token"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not token:
            logger.error(
                "github.token.decryption_returned_none",
                extra={"user_id": user_id, "oauth_id": str(oauth_identity.id)},
            )
            return Response(
                {"error": "Failed to decrypt GitHub token"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({"access_token": token})
