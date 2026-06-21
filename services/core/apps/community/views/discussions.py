import logging

import requests
from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..events import (
    publish_discussion_created,
    publish_discussion_deleted,
    publish_discussion_upvoted,
)
from ..permissions import IsAuthenticatedOrReadOnly
from ..serializers import (
    CreateDiscussionSerializer,
    DiscussionDetailSerializer,
    DiscussionListSerializer,
    UpdateDiscussionSerializer,
)
from ..services import DiscussionService, VoteService

logger = logging.getLogger(__name__)


def _resolve_profile(user_id: str) -> dict:
    identity_url = getattr(settings, "IDENTITY_SERVICE_URL", "http://identity:8001")
    endpoint = f"{identity_url}/api/profiles/internal/resolve-by-id/"
    try:
        resp = requests.post(
            endpoint,
            json={"user_ids": [user_id]},
            headers={
                getattr(settings, "INTERNAL_REQUEST_HEADER", "X-Internal-Request"): "1"
            },
            timeout=5,
        )
        if resp.status_code == 200:
            profiles = resp.json().get("profiles", {})
            return profiles.get(user_id, {})
    except requests.exceptions.RequestException:
        logger.warning("profile_resolve.failed", extra={"user_id": user_id})
    return {}


@extend_schema(tags=["Community"])
class DiscussionListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="List discussions",
        responses={200: OpenApiResponse(description="Paginated discussion list")},
    )
    def get(self, request: Request) -> Response:
        page = int(request.query_params.get("page", 1))
        tag = request.query_params.get("tag")
        sort = request.query_params.get("sort", "latest")
        workspace_id = request.query_params.get("workspace_id")
        items, total = DiscussionService.list_discussions(
            page=page,
            page_size=20,
            tag=tag,
            sort=sort,
            workspace_id=workspace_id,
            user_id=request.user_id,
        )
        serializer = DiscussionListSerializer(
            items, many=True, context={"request": request}
        )
        return Response(
            {"results": serializer.data, "total": total, "page": page, "page_size": 20}
        )

    @extend_schema(
        summary="Create discussion",
        request=CreateDiscussionSerializer,
        responses={201: DiscussionDetailSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = CreateDiscussionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        profile = _resolve_profile(request.user_id)
        discussion = DiscussionService.create_discussion(
            serializer.validated_data,
            user_id=request.user_id,
            username=profile.get("username", request.data.get("author_username", "")),
            display_name=profile.get(
                "display_name", request.data.get("author_display_name", "")
            ),
            avatar_url=profile.get(
                "avatar_url", request.data.get("author_avatar_url", "")
            ),
        )
        publish_discussion_created(discussion, request.user_id)
        return Response(
            DiscussionDetailSerializer(discussion, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Community"])
class DiscussionDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Get discussion", responses={200: DiscussionDetailSerializer}
    )
    def get(self, request: Request, discussion_id: str) -> Response:
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response(
                {"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            DiscussionDetailSerializer(discussion, context={"request": request}).data
        )

    @extend_schema(
        summary="Update discussion",
        request=UpdateDiscussionSerializer,
        responses={200: DiscussionDetailSerializer},
    )
    def patch(self, request: Request, discussion_id: str) -> Response:
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response(
                {"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if str(request.user_id) != str(discussion.author_id):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = UpdateDiscussionSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        discussion = DiscussionService.update_discussion(
            discussion,
            serializer.validated_data,
            tag_names=serializer.validated_data.get("tags"),
        )
        return Response(
            DiscussionDetailSerializer(discussion, context={"request": request}).data
        )

    @extend_schema(
        summary="Delete discussion",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, discussion_id: str) -> Response:
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response(
                {"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if str(request.user_id) != str(discussion.author_id):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        DiscussionService.soft_delete(discussion, request.user_id)
        publish_discussion_deleted(str(discussion.id), str(discussion.author_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Community"])
class DiscussionVoteView(APIView):
    @extend_schema(
        summary="Vote on discussion",
        responses={200: OpenApiResponse(description="Vote recorded")},
    )
    def post(self, request: Request, discussion_id: str) -> Response:
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response(
                {"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND
            )
        value = request.data.get("value", 1)
        if value not in (1, -1):
            return Response(
                {"detail": "Value must be 1 (upvote) or -1 (downvote)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        vote, action = VoteService.vote_discussion(discussion, request.user_id, value)
        if action != "no_change":
            publish_discussion_upvoted(discussion, request.user_id)
        return Response({"value": vote.value, "action": action})

    @extend_schema(
        summary="Remove discussion vote",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, discussion_id: str) -> Response:
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response(
                {"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND
            )
        VoteService.remove_discussion_vote(discussion, request.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Community"])
class TrendingDiscussionsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Get trending discussions",
        responses={200: OpenApiResponse(description="Trending discussions")},
    )
    def get(self, request: Request) -> Response:
        limit = int(request.query_params.get("limit", 10))
        discussions = DiscussionService.get_trending(limit=limit)
        return Response({"results": discussions})
