from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated
from apps.workspaces.selectors import WorkspaceSelector

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

        # SECURITY: the `workspace` query param is attacker-controlled. Without
        # this check any authenticated user could read another workspace's
        # projects, tasks, knowledge assets, repos and notifications by ID.
        # Returns 404 (not 403) so membership is not confirmed or denied.
        workspace = WorkspaceSelector.get_workspace_for_user(
            workspace_id, request.user_id
        )
        if workspace is None:
            raise NotFound("Workspace not found.")

        service = SearchService()
        user_id = str(request.user_id)

        result = service.search(
            query=query,
            workspace_id=workspace_id,
            user_id=user_id,
            scope=scope,
            page=page,
            page_size=page_size,
        )

        return Response(result)
