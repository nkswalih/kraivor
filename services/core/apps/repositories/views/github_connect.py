import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


@extend_schema(tags=["Repositories"])
class GitHubOAuthConnectView(APIView):
    @extend_schema(summary="GitHub OAuth connect URL")
    def get(self, request: Request) -> Response:
        client_id = getattr(settings, "GITHUB_CLIENT_ID", "")
        redirect_uri = getattr(settings, "GITHUB_CONNECT_REDIRECT_URI", "")
        state = request.query_params.get("state", "")
        if not client_id:
            return Response(
                {"detail": "GitHub OAuth is not configured."},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        url = (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=read:user,user:email"
            f"&state={state}"
        )
        return Response({"authorization_url": url})
