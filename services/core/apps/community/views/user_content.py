import uuid

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Comment, Discussion
from ..permissions import IsAuthenticatedOrReadOnly
from ..serializers import CommentSerializer, DiscussionListSerializer


def list_discussions_by_author(author_id: uuid.UUID | str, page: int = 1, page_size: int = 20):
    from ..services import DiscussionService

    qs = Discussion.objects.filter(author_id=author_id).prefetch_related("tags")
    total = qs.count()
    offset = (page - 1) * page_size
    items = qs[offset : offset + page_size]
    return items, total


def list_comments_by_author(author_id: uuid.UUID | str, page: int = 1, page_size: int = 30):
    qs = Comment.objects.filter(author_id=author_id, parent__isnull=True).select_related(None)
    total = qs.count()
    offset = (page - 1) * page_size
    items = qs[offset : offset + page_size]
    return items, total


class UserDiscussionsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        tags=["Community"],
        summary="List user discussions",
        description="Returns paginated discussions authored by the given user.",
        responses={200: OpenApiResponse(description="Paginated user discussion list")},
    )
    def get(self, request: Request, user_id: uuid.UUID) -> Response:
        page = int(request.query_params.get("page", 1))
        items, total = list_discussions_by_author(user_id, page=page)
        serializer = DiscussionListSerializer(items, many=True, context={"request": request})
        return Response(
            {"results": serializer.data, "total": total, "page": page, "page_size": 20}
        )


class UserCommentsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    @extend_schema(
        tags=["Community"],
        summary="List user comments",
        description="Returns paginated comments authored by the given user.",
        responses={200: OpenApiResponse(description="Paginated user comment list")},
    )
    def get(self, request: Request, user_id: uuid.UUID) -> Response:
        page = int(request.query_params.get("page", 1))
        items, total = list_comments_by_author(user_id, page=page)
        serializer = CommentSerializer(items, many=True, context={"request": request})
        return Response(
            {"results": serializer.data, "total": total, "page": page, "page_size": 30}
        )
