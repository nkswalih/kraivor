from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import SearchService


class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "").strip()
        workspace_id = request.query_params.get("workspace")
        scope = request.query_params.get("scope", "all")
        page = int(request.query_params.get("page", "1"))
        page_size = int(request.query_params.get("page_size", "20"))

        if not workspace_id:
            return Response(
                {"error": "workspace parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(query) < 2:
            return Response(
                {
                    "query": query,
                    "total_results": 0,
                    "page": page,
                    "page_size": page_size,
                    "results": [],
                    "facets": {},
                }
            )

        page_size = min(page_size, 50)
        page = max(page, 1)

        service = SearchService()
        user_id = str(request.user.pk) if request.user.is_authenticated else None

        result = service.search(
            query=query,
            workspace_id=workspace_id,
            user_id=user_id,
            scope=scope,
            page=page,
            page_size=page_size,
        )

        return Response(result)
