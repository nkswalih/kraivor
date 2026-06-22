import logging
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..events import publish_comment_created
from ..permissions import IsAuthenticatedOrReadOnly
from ..serializers import CommentSerializer, CreateCommentSerializer
from ..services import CommentService, DiscussionService, VoteService
from .discussions import _resolve_profile

logger = logging.getLogger(__name__)


@extend_schema(tags=["Community"])
class CommentListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="List comments",
        responses={200: OpenApiResponse(description="Paginated comment list")},
    )
    def get(self, request: Request, discussion_id: str) -> Response:
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response(
                {"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND
            )
        page = int(request.query_params.get("page", 1))
        sort = request.query_params.get("sort", "newest")
        items, total = CommentService.get_comments(
            discussion_id,
            page=page,
            page_size=30,
            sort=sort,
            user_id=request.user_id,
        )
        serializer = CommentSerializer(items, many=True, context={"request": request})
        return Response(
            {"results": serializer.data, "total": total, "page": page, "page_size": 30}
        )

    @extend_schema(
        summary="Create comment",
        request=CreateCommentSerializer,
        responses={201: CommentSerializer},
    )
    def post(self, request: Request, discussion_id: str) -> Response:
        discussion = DiscussionService.get_detail(discussion_id)
        if not discussion:
            return Response(
                {"detail": "Discussion not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = CreateCommentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        profile = _resolve_profile(request.user_id)
        comment = CommentService.create_comment(
            discussion,
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
        publish_comment_created(comment, request.user_id)
        return Response(
            CommentSerializer(comment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Community"])
class CommentRepliesView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        summary="List comment replies", responses={200: CommentSerializer(many=True)}
    )
    def get(self, request: Request, discussion_id: str, comment_id: str) -> Response:
        replies = CommentService.get_replies(comment_id, user_id=request.user_id)
        return Response(
            CommentSerializer(replies, many=True, context={"request": request}).data
        )


@extend_schema(tags=["Community"])
class CommentVoteView(APIView):
    @extend_schema(
        summary="Vote on comment",
        responses={200: OpenApiResponse(description="Vote recorded")},
    )
    def post(self, request: Request, discussion_id: str, comment_id: str) -> Response:
        comment = CommentService.get_by_id(comment_id, discussion_id)
        if not comment:
            return Response(
                {"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND
            )
        value = request.data.get("value", 1)
        if value not in (1, -1):
            return Response(
                {"detail": "Value must be 1 (upvote) or -1 (downvote)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        vote, action = VoteService.vote_comment(comment, request.user_id, value)
        return Response({"value": vote.value, "action": action})

    @extend_schema(
        summary="Remove comment vote",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, discussion_id: str, comment_id: str) -> Response:
        comment = CommentService.get_by_id(comment_id, discussion_id)
        if not comment:
            return Response(
                {"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND
            )
        VoteService.remove_comment_vote(comment, request.user_id)
        return Response(status=status.HTTP_204_NO_CONTENT)
