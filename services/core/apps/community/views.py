import logging

import requests
from django.conf import settings
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .events import (
    publish_comment_created,
    publish_discussion_created,
    publish_discussion_deleted,
    publish_discussion_upvoted,
)
from .permissions import IsAuthenticatedOrReadOnly
from .serializers import (
    CommentSerializer,
    CreateCommentSerializer,
    CreateDiscussionSerializer,
    DiscussionDetailSerializer,
    DiscussionListSerializer,
    TagSerializer,
    UpdateDiscussionSerializer,
)
from .services import CommentService, DiscussionService, TagService, VoteService

logger = logging.getLogger(__name__)

PAGE_SIZE = 20
COMMENT_PAGE_SIZE = 30


def _resolve_profile(user_id: str) -> dict:
    """Fetch profile data (username, display_name, avatar_url) from auth service."""
    identity_url = getattr(settings, "IDENTITY_SERVICE_URL", "http://identity:8001")
    endpoint = f"{identity_url}/api/profiles/internal/resolve-by-id/"
    try:
        resp = requests.post(
            endpoint,
            json={"user_ids": [user_id]},
            headers={getattr(settings, "INTERNAL_REQUEST_HEADER", "X-Internal-Request"): "1"},
            timeout=5,
        )
        if resp.status_code == 200:
            profiles = resp.json().get("profiles", {})
            return profiles.get(user_id, {})
    except requests.exceptions.RequestException:
        logger.warning("profile_resolve.failed", extra={"user_id": user_id})
    return {}


class DiscussionListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="List discussions",
        tags=["Community"],
        responses={200: OpenApiResponse(description="Paginated discussion list")},
    )
    def get(self, request):
        page = int(request.query_params.get("page", 1))
        tag = request.query_params.get("tag")
        sort = request.query_params.get("sort", "latest")
        workspace_id = request.query_params.get("workspace_id")
        items, total = DiscussionService.list_discussions(
            page=page, page_size=PAGE_SIZE, tag=tag, sort=sort, workspace_id=workspace_id
        )
        serializer = DiscussionListSerializer(items, many=True, context={"request": request})
        return Response(
            {
                "results": serializer.data,
                "total": total,
                "page": page,
                "page_size": PAGE_SIZE,
            }
        )

    @extend_schema(
        summary="Create discussion",
        tags=["Community"],
        request=CreateDiscussionSerializer,
        responses={201: DiscussionDetailSerializer},
    )
    def post(self, request):
        serializer = CreateDiscussionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        profile = _resolve_profile(request.user_id)
        discussion = DiscussionService.create_discussion(
            serializer.validated_data,
            user_id=request.user_id,
            username=profile.get("username", request.data.get("author_username", "")),
            display_name=profile.get("display_name", request.data.get("author_display_name", "")),
            avatar_url=profile.get("avatar_url", request.data.get("author_avatar_url", "")),
        )
        publish_discussion_created(discussion, request.user_id)
        return Response(
            DiscussionDetailSerializer(discussion, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class DiscussionDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Get discussion",
        tags=["Community"],
        responses={200: DiscussionDetailSerializer},
    )
    def get(self, request, discussion_id):
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response({"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            DiscussionDetailSerializer(discussion, context={"request": request}).data
        )

    @extend_schema(
        summary="Update discussion",
        tags=["Community"],
        request=UpdateDiscussionSerializer,
        responses={200: DiscussionDetailSerializer},
    )
    def patch(self, request, discussion_id):
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response({"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND)
        if str(request.user_id) != str(discussion.author_id):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        serializer = UpdateDiscussionSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        discussion = DiscussionService.update_discussion(
            discussion, serializer.validated_data, tag_names=serializer.validated_data.get("tags")
        )
        return Response(
            DiscussionDetailSerializer(discussion, context={"request": request}).data
        )

    @extend_schema(
        summary="Delete discussion",
        tags=["Community"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request, discussion_id):
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response({"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND)
        if str(request.user_id) != str(discussion.author_id):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        DiscussionService.soft_delete(discussion, request.user_id)
        publish_discussion_deleted(str(discussion.id), str(discussion.author_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class DiscussionVoteView(APIView):
    @extend_schema(
        summary="Vote on discussion",
        tags=["Community"],
        responses={200: OpenApiResponse(description="Vote recorded")},
    )
    def post(self, request, discussion_id):
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response({"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND)
        value = request.data.get("value", 1)
        if value not in (1, -1):
            return Response({"detail": "Value must be 1 (upvote) or -1 (downvote)."}, status=status.HTTP_400_BAD_REQUEST)
        vote, action = VoteService.vote_discussion(discussion, request.user_id, value)
        if action != "no_change":
            publish_discussion_upvoted(discussion, request.user_id)
        return Response({"value": vote.value, "action": action})

    @extend_schema(
        summary="Remove discussion vote",
        tags=["Community"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request, discussion_id):
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response({"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND)
        VoteService.remove_discussion_vote(discussion, request.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CommentListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="List comments",
        tags=["Community"],
        responses={200: OpenApiResponse(description="Paginated comment list")},
    )
    def get(self, request, discussion_id):
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response({"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND)
        page = int(request.query_params.get("page", 1))
        sort = request.query_params.get("sort", "newest")
        items, total = CommentService.get_comments(discussion_id, page=page, page_size=COMMENT_PAGE_SIZE, sort=sort)
        serializer = CommentSerializer(items, many=True, context={"request": request})
        return Response(
            {
                "results": serializer.data,
                "total": total,
                "page": page,
                "page_size": COMMENT_PAGE_SIZE,
            }
        )

    @extend_schema(
        summary="Create comment",
        tags=["Community"],
        request=CreateCommentSerializer,
        responses={201: CommentSerializer},
    )
    def post(self, request, discussion_id):
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response({"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = CreateCommentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        profile = _resolve_profile(request.user_id)
        comment = CommentService.create_comment(
            discussion,
            serializer.validated_data,
            user_id=request.user_id,
            username=profile.get("username", request.data.get("author_username", "")),
            display_name=profile.get("display_name", request.data.get("author_display_name", "")),
            avatar_url=profile.get("avatar_url", request.data.get("author_avatar_url", "")),
        )
        publish_comment_created(comment, request.user_id)
        return Response(
            CommentSerializer(comment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class CommentRepliesView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="List comment replies",
        tags=["Community"],
        responses={200: CommentSerializer(many=True)},
    )
    def get(self, request, discussion_id, comment_id):
        replies = CommentService.get_replies(comment_id)
        return Response(
            CommentSerializer(replies, many=True, context={"request": request}).data
        )


class CommentVoteView(APIView):
    @extend_schema(
        summary="Vote on comment",
        tags=["Community"],
        responses={200: OpenApiResponse(description="Vote recorded")},
    )
    def post(self, request, discussion_id, comment_id):
        comment = CommentService.get_by_id(comment_id, discussion_id)
        if not comment:
            return Response({"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)
        value = request.data.get("value", 1)
        if value not in (1, -1):
            return Response({"detail": "Value must be 1 (upvote) or -1 (downvote)."}, status=status.HTTP_400_BAD_REQUEST)
        vote, action = VoteService.vote_comment(comment, request.user_id, value)
        return Response({"value": vote.value, "action": action})

    @extend_schema(
        summary="Remove comment vote",
        tags=["Community"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request, discussion_id, comment_id):
        comment = CommentService.get_by_id(comment_id, discussion_id)
        if not comment:
            return Response({"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND)
        VoteService.remove_comment_vote(comment, request.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TrendingDiscussionsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Get trending discussions",
        tags=["Community"],
        responses={200: OpenApiResponse(description="Trending discussions")},
    )
    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        discussions = DiscussionService.get_trending(limit=limit)
        return Response({"results": discussions})


class PopularTagsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Get popular tags",
        tags=["Community"],
        responses={200: OpenApiResponse(description="Popular tags")},
    )
    def get(self, request):
        limit = int(request.query_params.get("limit", 20))
        tags = TagService.get_popular_tags(limit=limit)
        return Response({"results": TagSerializer(tags, many=True).data})


class TagSearchView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="Search tags",
        tags=["Community"],
        responses={200: OpenApiResponse(description="Tag search results")},
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)
        tags = TagService.search_tags(query)
        return Response({"results": TagSerializer(tags, many=True).data})
