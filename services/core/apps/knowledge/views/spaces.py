from typing import TYPE_CHECKING

import uuid
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated

if TYPE_CHECKING:
    from apps.knowledge.models import KnowledgeSpace
    from apps.workspaces.models import Workspace

from ..selectors.knowledge_selectors import KnowledgeSpaceSelector
from ..serializers import (
    KnowledgeSpaceCreateSerializer,
    KnowledgeSpaceListSerializer,
    KnowledgeSpaceSerializer,
    KnowledgeSpaceUpdateSerializer,
)
from ..services import KnowledgeSpaceService
from ..services.base import KnowledgePermissionError

logger = __import__("logging").getLogger(__name__)


def _get_space_or_404(pk: str, user_id: str) -> "KnowledgeSpace":
    try:
        ks_id = pk if isinstance(pk, uuid.UUID) else uuid.UUID(str(pk))
    except (ValueError, AttributeError) as exc:
        raise NotFound("Knowledge space not found.") from exc
    ks = KnowledgeSpaceSelector.get_detail(ks_id)
    if not ks or not ks.workspace.is_member(user_id):
        raise NotFound("Knowledge space not found.")
    return ks


class WorkspaceContextMixin:
    def _get_user_id(self) -> str:
        return self.request.user_id

    def _get_workspace_or_404(self, workspace_pk: str) -> "Workspace":
        from apps.workspaces.selectors import WorkspaceSelector

        workspace = WorkspaceSelector.get_workspace_for_user(
            workspace_pk, self._get_user_id()
        )
        if not workspace:
            raise NotFound("Workspace not found.")
        return workspace


@extend_schema(tags=["Knowledge"])
class KnowledgeSpaceListView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List knowledge spaces",
        responses={200: KnowledgeSpaceListSerializer(many=True)},
    )
    def get(self, request: Request, workspace_pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        search = request.query_params.get("search", "").strip() or None
        spaces = KnowledgeSpaceService().list_knowledge_spaces(
            workspace=workspace, search=search
        )
        return Response(KnowledgeSpaceListSerializer(spaces, many=True).data)

    @extend_schema(
        summary="Create knowledge space",
        request=KnowledgeSpaceCreateSerializer,
        responses={201: KnowledgeSpaceSerializer},
    )
    def post(self, request: Request, workspace_pk: str | None = None) -> Response:
        workspace = self._get_workspace_or_404(workspace_pk)
        serializer = KnowledgeSpaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            space = KnowledgeSpaceService().create_knowledge_space(
                workspace=workspace, actor_id=request.user_id, **serializer.validated_data
            )
        except KnowledgePermissionError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_403_FORBIDDEN
            )
        return Response(
            KnowledgeSpaceSerializer(space).data, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Knowledge"])
class KnowledgeSpaceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get knowledge space", responses={200: KnowledgeSpaceSerializer}
    )
    def get(self, request: Request, pk: str | None = None) -> Response:
        space = _get_space_or_404(pk, request.user_id)
        return Response(KnowledgeSpaceSerializer(space).data)

    @extend_schema(
        summary="Update knowledge space",
        request=KnowledgeSpaceUpdateSerializer,
        responses={200: KnowledgeSpaceSerializer},
    )
    def patch(self, request: Request, pk: str | None = None) -> Response:
        space = _get_space_or_404(pk, request.user_id)
        serializer = KnowledgeSpaceUpdateSerializer(
            space, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        try:
            updated = KnowledgeSpaceService().update_knowledge_space(
                knowledge_space=space, actor_id=request.user_id, updates=serializer.validated_data
            )
        except KnowledgePermissionError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_403_FORBIDDEN
            )
        return Response(KnowledgeSpaceSerializer(updated).data)
    
    @extend_schema(
        summary="Delete knowledge space",
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request: Request, pk: str | None = None) -> Response:
        space = _get_space_or_404(pk, request.user_id)
        try:
            KnowledgeSpaceService().delete_knowledge_space(
                knowledge_space=space, actor_id=request.user_id
            )
        except KnowledgePermissionError as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_403_FORBIDDEN
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
