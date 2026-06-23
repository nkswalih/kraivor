from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.models import Workspace
from apps.workspaces.permissions import IsAuthenticated
from apps.workspaces.selectors import WorkspaceSelector
from apps.workspaces.serializers import (
    WorkspaceCreateSerializer,
    WorkspaceDetailSerializer,
    WorkspaceListSerializer,
    WorkspaceUpdateSerializer,
)
from apps.workspaces.services import (
    WorkspaceLimitError,
    WorkspacePermissionError,
    WorkspaceService,
)
from core.pagination import CursorPagination

logger = __import__("logging").getLogger(__name__)


@extend_schema(tags=["Workspaces"])
class WorkspaceListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = CursorPagination

    @extend_schema(
        summary="List workspaces",
        responses={200: WorkspaceListSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        user_id = request.user_id
        workspaces = WorkspaceSelector.list_user_workspaces(user_id)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(workspaces, request)
        serializer = WorkspaceListSerializer(
            page, many=True, context={"request": request}
        )
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create workspace",
        request=WorkspaceCreateSerializer,
        responses={201: WorkspaceDetailSerializer},
    )
    def post(self, request: Request) -> Response:
        user_id = request.user_id
        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            workspace = WorkspaceService().create_workspace(
                owner_id=user_id,
                name=validated["name"],
                slug=validated["slug"],
                avatar_url=validated.get("avatar_url"),
                description=validated.get("description"),
                settings=validated.get("settings", {}),
            )
        except WorkspaceLimitError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        workspace = WorkspaceSelector.get_annotated_detail(workspace.id)
        return Response(
            WorkspaceDetailSerializer(workspace, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["Workspaces"])
class WorkspaceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_workspace_or_404(self, pk: str, user_id: str) -> Workspace:
        workspace = WorkspaceSelector.get_workspace_for_user(pk, user_id)
        if not workspace:
            raise NotFound("Workspace not found.")
        return workspace

    @extend_schema(
        summary="Get workspace",
        responses={200: WorkspaceDetailSerializer},
    )
    def get(self, request: Request, pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(pk, request.user_id)
        return Response(
            WorkspaceDetailSerializer(workspace, context={"request": request}).data
        )

    @extend_schema(
        summary="Update workspace",
        request=WorkspaceUpdateSerializer,
        responses={200: WorkspaceDetailSerializer},
    )
    def patch(self, request: Request, pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(pk, request.user_id)
        serializer = WorkspaceUpdateSerializer(
            workspace, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        try:
            updated = WorkspaceService().update_workspace(
                workspace=workspace,
                actor_id=request.user_id,
                updates=serializer.validated_data,
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            WorkspaceDetailSerializer(updated, context={"request": request}).data
        )

    @extend_schema(
        summary="Delete workspace",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(pk, request.user_id)
        try:
            WorkspaceService().delete_workspace(
                workspace=workspace, actor_id=request.user_id
            )
        except WorkspacePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
