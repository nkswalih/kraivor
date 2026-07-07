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
from apps.notifications.tasks import dispatch_notification
from apps.notifications.utils import fanout_to_workspace_members

logger = logging.getLogger(__name__)


def _identity_endpoint(path: str) -> str:
    base = getattr(settings, "IDENTITY_SERVICE_URL", "http://identity:8001/api")
    if base.endswith("/api"):
        base = base[:-4]
    return f"{base}/api{path}"


def _resolve_profile(user_id: str) -> dict:
    endpoint = _identity_endpoint("/profiles/internal/resolve-by-id/")
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


def _sync_profile_counters(event_type: str, author_id: str) -> None:
    endpoint = _identity_endpoint("/profiles/internal/community-event/")
    try:
        resp = requests.post(
            endpoint,
            json={"event_type": event_type, "author_id": author_id},
            headers={
                getattr(settings, "INTERNAL_REQUEST_HEADER", "X-Internal-Request"): "1"
            },
            timeout=5,
        )
        if resp.status_code != 200:
            logger.warning(
                "profile_sync.failed",
                extra={"event_type": event_type, "author_id": author_id, "status": resp.status_code},
            )
    except requests.exceptions.RequestException as exc:
        logger.warning(
            "profile_sync.error",
            extra={"event_type": event_type, "author_id": author_id, "error": str(exc)},
        )


class DiscussionListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        tags=["Community"],
        summary="List discussions",
        responses={200: OpenApiResponse(description="Paginated discussion list")},
    )
    def get(self, request: Request) -> Response:
        page = int(request.query_params.get("page", 1))
        tag = request.query_params.get("tag")
        sort = request.query_params.get("sort", "latest")
        search = request.query_params.get("search")
        workspace_id = request.query_params.get("workspace_id")
        items, total = DiscussionService.list_discussions(
            page=page,
            page_size=20,
            tag=tag,
            sort=sort,
            search=search,
            workspace_id=workspace_id,
            user_id=getattr(request, "user_id", None),
        )
        serializer = DiscussionListSerializer(
            items, many=True, context={"request": request}
        )
        return Response(
            {"results": serializer.data, "total": total, "page": page, "page_size": 20}
        )

    @extend_schema(
        tags=["Community"],
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
        _sync_profile_counters("discussion.created", str(discussion.author_id))

        workspace_id = serializer.validated_data.get("workspace_id")
        if workspace_id:
            fanout_to_workspace_members(
                workspace_id=str(workspace_id),
                notification_type="community.discussion.created",
                title=f"New discussion: {discussion.title}",
                body=f"A new discussion '{discussion.title}' was created.",
                link=f"/community/discussions/{discussion.id}",
                actor_id=str(request.user_id),
                exclude_user_id=str(request.user_id),
            )

        return Response(
            DiscussionDetailSerializer(discussion, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class DiscussionDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        tags=["Community"],
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
        tags=["Community"],
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
        tags=["Community"],
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
        _sync_profile_counters("discussion.deleted", str(discussion.author_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class DiscussionVoteView(APIView):
    @extend_schema(
        tags=["Community"],
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
            event_type = "discussion.upvoted" if value == 1 else "discussion.downvoted"
            _sync_profile_counters(event_type, str(discussion.author_id))

            if value == 1 and str(discussion.author_id) != str(request.user_id):
                voter_name = getattr(request, "user_name", "Someone")
                dispatch_notification.delay(
                    user_id=str(discussion.author_id),
                    notification_type="community.discussion.upvoted",
                    title="Your discussion was upvoted",
                    body=f"{voter_name} upvoted your discussion '{discussion.title}'.",
                    link=f"/community/discussions/{discussion.id}",
                    actor_id=str(request.user_id),
                )

        return Response({"value": vote.value, "action": action})

    @extend_schema(
        tags=["Community"],
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


class TrendingDiscussionsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        tags=["Community"],
        summary="Get trending discussions",
        responses={200: OpenApiResponse(description="Trending discussions")},
    )
    def get(self, request: Request) -> Response:
        limit = int(request.query_params.get("limit", 10))
        discussions = DiscussionService.get_trending(limit=limit)
        return Response({"results": discussions})
