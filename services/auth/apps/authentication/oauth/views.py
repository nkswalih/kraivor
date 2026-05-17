"""
GitHub OAuth Views
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .encryption import get_encryption_service
from .github import GitHubOAuthError, get_github_oauth_service
from .state_manager import OAuthStateError, get_state_manager
from ..services import create_tokens_for_user
from ..services.user_service import find_or_create_oauth_user

logger = logging.getLogger(__name__)


class GitHubOAuthInitiateView(APIView):
    permission_classes = [AllowAny]

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
            return Response({"error": "OAuth initialization failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GitHubOAuthCallbackView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code or not state:
            return Response({"error": "Missing code or state parameter"}, status=status.HTTP_400_BAD_REQUEST)

        provider = "github"
        try:
            state_manager = get_state_manager()
            if not state_manager.validate_state(provider, state):
                return Response({"error": "Invalid or expired state token"}, status=status.HTTP_400_BAD_REQUEST)

            oauth_service = get_github_oauth_service()
            access_token = oauth_service.exchange_code_for_token(code)
            github_user = oauth_service.get_user(access_token)

            if not github_user.email:
                primary_email = oauth_service.get_primary_verified_email(access_token)
                github_user.email = primary_email

            if not github_user.email:
                return Response({"error": "GitHub email not available. Ensure your GitHub account has a verified primary email."}, status=status.HTTP_400_BAD_REQUEST)

            user, created = find_or_create_oauth_user(provider=provider, oauth_id=str(github_user.id), email=github_user.email, name=github_user.name, avatar_url=github_user.avatar_url)

            encryption_service = get_encryption_service()
            encrypted_token = encryption_service.encrypt(access_token)
            user.oauth_identities.filter(provider=provider, deleted_at__isnull=False).update(deleted_at=None, access_token_encrypted=encrypted_token)

            tokens = create_tokens_for_user(user)
            return Response({"user": {"id": str(user.id), "email": user.email, "name": user.name}, "tokens": tokens}, status=status.HTTP_200_OK)
        except (OAuthStateError, GitHubOAuthError) as e:
            logger.error("oauth_callback_failed", extra={"error": str(e)})
            return Response({"error": "OAuth authentication failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)