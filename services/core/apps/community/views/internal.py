import logging
import uuid

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..tasks import update_author_denormalization

logger = logging.getLogger(__name__)


class SyncAuthorDenormalizationView(APIView):
    """
    POST /api/community/internal/sync-author/

    Internal endpoint. Updates denormalized author fields (username, display_name, avatar_url)
    on all discussions and comments by the given author. Called by the auth service when
    a profile is updated (username change, display name change, avatar change).

    Request:
      {"author_id": "uuid", "username": "new_username", "display_name": "New Name", "avatar_url": "..."}

    Security:
      - Requires X-Internal-Request header
    """

    permission_classes = []

    def post(self, request):
        internal_header = getattr(settings, "INTERNAL_REQUEST_HEADER", "X-Internal-Request")
        if request.headers.get(internal_header) != "1":
            return Response({"error": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        author_id = request.data.get("author_id")
        username = request.data.get("username")
        display_name = request.data.get("display_name")
        avatar_url = request.data.get("avatar_url", "")

        if not all([author_id, username, display_name]):
            return Response(
                {"error": "author_id, username, and display_name are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            uuid.UUID(author_id)
        except (ValueError, TypeError):
            return Response({"error": "Invalid author_id"}, status=status.HTTP_400_BAD_REQUEST)

        update_author_denormalization.delay(author_id, username, display_name, avatar_url)

        return Response({"processed": True})
