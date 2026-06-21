from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..serializers import TagSerializer
from ..services import TagService


@extend_schema(tags=["Community"])
class PopularTagsView(APIView):
    @extend_schema(summary="Get popular tags")
    def get(self, request: Request) -> Response:
        limit = int(request.query_params.get("limit", 20))
        tags = TagService.get_popular_tags(limit=limit)
        return Response({"results": TagSerializer(tags, many=True).data})


@extend_schema(tags=["Community"])
class TagSearchView(APIView):
    @extend_schema(summary="Search tags")
    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"detail": "Query parameter 'q' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        tags = TagService.search_tags(query)
        return Response({"results": TagSerializer(tags, many=True).data})
