"""
GitHub OAuth Views
"""

import logging
from django.conf import settings
from django.shortcuts import redirect
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..jwt import generate_token_pair
from ..services.user_service import find_or_create_oauth_user
from .encryption import get_encryption_service
from .github import GitHubOAuthError, get_github_oauth_service
from .state_manager import OAuthStateError, get_state_manager

logger = logging.getLogger(__name__)


class GitHubOAuthInitiateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Initiate GitHub OAuth",
        description="Returns GitHub OAuth authorization URL for user login.",
        tags=["Authentication"],
        responses={200: OpenApiResponse(description="Authorization URL")},
    )
    def get(self, request: Request) -> Response:
        provider = "github"
        try:
            state_manager = get_state_manager()
            state = state_manager.generate_state(provider)
            oauth_service = get_github_oauth_service()
            auth_url = oauth_service.get_authorization_url(state)
            return Response({"authorization_url": auth_url}, status=status.HTTP_200_OK)
        except (OAuthStateError, GitHubOAuthError) as e:
            logger.error("oauth_initiate_failed", extra={"error": str(e)})
            return Response(
                {"error": "OAuth initialization failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GitHubOAuthCallbackView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="GitHub OAuth callback",
        description="Handles the GitHub OAuth callback, exchanges authorization code for tokens, and creates/finds the user.",
        tags=["Authentication"],
        responses={302: OpenApiResponse(description="Redirect with JWT tokens")},
    )
    def get(self, request: Request) -> Response:
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code or not state:
            return Response(
                {"error": "Missing code or state parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Detect whether this is a repo-connect flow vs login by trying
        # the "github_connect" state provider first, falling back to "github".
        state_manager = get_state_manager()
        is_connect = state_manager.validate_state("github_connect", state)
        if not is_connect and not state_manager.validate_state("github", state):
            return Response(
                {"error": "Invalid or expired state token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider = "github"
        try:
            oauth_service = get_github_oauth_service()
            access_token = oauth_service.exchange_code_for_token(code)
            github_user = oauth_service.get_user(access_token)

            if not github_user.email:
                primary_email = oauth_service.get_primary_verified_email(access_token)
                github_user.email = primary_email

            if not github_user.email:
                return Response(
                    {
                        "error": "GitHub email not available. Ensure your GitHub account has a verified primary email."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user, created = find_or_create_oauth_user(
                provider=provider,
                oauth_id=str(github_user.id),
                email=github_user.email,
                name=github_user.name,
                avatar_url=github_user.avatar_url,
            )

            # Store the encrypted token on the active OAuth identity.
            # Fix: was deleted_at__isnull=False (deleted identities only).
            encryption_service = get_encryption_service()
            encrypted_token = encryption_service.encrypt(access_token)
            user.oauth_identities.filter(
                provider=provider, deleted_at__isnull=True
            ).update(access_token_encrypted=encrypted_token)

            # If no active identity matched (e.g. first-time creation where the
            # identity was just created with NULL deleted_at but the filter still
            # missed it — edge case race), fall back to setting it directly.
            if not user.oauth_identities.filter(
                provider=provider,
                deleted_at__isnull=True,
                access_token_encrypted=encrypted_token,
            ).exists():
                user.oauth_identities.filter(provider=provider).update(
                    access_token_encrypted=encrypted_token
                )

            tokens = generate_token_pair(user)
            frontend_url = (
                f"{settings.FRONTEND_URL}/oauth/success"
                f"?access_token={tokens['access_token']}"
            )

            # For repo-connect flow, signal the frontend to redirect to repos page
            if is_connect:
                frontend_url += "&github_connect=1"

            response = redirect(frontend_url)

            response.set_cookie(
                key="refresh_token",
                value=tokens["refresh_token"],
                httponly=True,
                secure=False,  # True in production HTTPS
                samesite="Lax",
                max_age=60 * 60 * 24 * 7,
            )

            return response
        except (OAuthStateError, GitHubOAuthError) as e:
            logger.error("oauth_callback_failed", extra={"error": str(e)})
            return Response(
                {"error": "OAuth authentication failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GitHubConnectView(APIView):
    """
    GET /api/auth/oauth/github/connect/

    Returns GitHub OAuth URL with 'repo' scope for connecting a repository.
    Frontend redirects the user to this URL to authorize repo access.

    Uses "github_connect" state provider so the callback can differentiate
    repo-connect flows from login flows and redirect the user back to the
    repositories page instead of the dashboard.
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Connect GitHub repo",
        description="Returns GitHub OAuth URL with repo scope for connecting a repository to Kraivor.",
        tags=["Authentication"],
        responses={
            200: OpenApiResponse(description="Authorization URL with repo scope")
        },
    )
    def get(self, request):
        state_manager = get_state_manager()
        state = state_manager.generate_state("github_connect")

        # Build authorization URL with repo scope
        from urllib.parse import urlencode

        client_id = getattr(settings, "GITHUB_CLIENT_ID", "")
        redirect_uri = getattr(
            settings,
            "GITHUB_REPO_CONNECT_REDIRECT_URI",
            getattr(settings, "GITHUB_REDIRECT_URI", ""),
        )

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "user:email read:user repo",  # full repo scope
            "state": state,
        }

        auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"

        return Response({"authorization_url": auth_url})
