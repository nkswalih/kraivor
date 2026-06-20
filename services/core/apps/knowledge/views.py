import logging
import uuid

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated
from apps.workspaces.views import WorkspaceContextMixin

from .models import KnowledgeAsset, KnowledgeSpace
from .serializers import (
    KnowledgeAssetInputSerializer,
    KnowledgeAssetSerializer,
    KnowledgeSpaceCreateSerializer,
    KnowledgeSpaceListSerializer,
    KnowledgeSpaceSerializer,
    KnowledgeSpaceUpdateSerializer,
)
from .services import (
    KnowledgeAssetService,
    KnowledgePermissionError,
    KnowledgeSpaceService,
)

logger = logging.getLogger(__name__)


def _get_knowledge_space_or_404(pk, user_id) -> KnowledgeSpace:
    """
    Shared helper: fetch a knowledge space by UUID and verify workspace membership.

    Returns 404 for both "doesn't exist" and "requesting user is not a
    workspace member" to avoid leaking information about workspace contents
    to outsiders.
    """
    try:
        ks_id = pk if isinstance(pk, uuid.UUID) else uuid.UUID(str(pk))
    except (ValueError, AttributeError) as exc:
        raise NotFound("Knowledge space not found.") from exc

    ks = KnowledgeSpace.objects.select_related("workspace").filter(id=ks_id).first()

    if not ks or not ks.workspace.is_member(user_id):
        raise NotFound("Knowledge space not found.")

    return ks


class KnowledgeSpaceListCreateView(WorkspaceContextMixin, APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List knowledge spaces",
        tags=["Knowledge"],
        responses={200: KnowledgeSpaceListSerializer(many=True)},
    )
    def get(self, request, workspace_pk=None):
        workspace = self._get_workspace_or_404(workspace_pk)
        search = request.query_params.get("search", "").strip() or None

        knowledge_spaces = KnowledgeSpaceService().list_knowledge_spaces(
            workspace=workspace, search=search
        )
        return Response(KnowledgeSpaceListSerializer(knowledge_spaces, many=True).data)

    @extend_schema(
        summary="Create knowledge space",
        tags=["Knowledge"],
        request=KnowledgeSpaceCreateSerializer,
        responses={201: KnowledgeSpaceSerializer},
    )
    def post(self, request, workspace_pk=None):
        workspace = self._get_workspace_or_404(workspace_pk)

        serializer = KnowledgeSpaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        try:
            knowledge_space = KnowledgeSpaceService().create_knowledge_space(
                workspace=workspace,
                actor_id=self._get_user_id(),
                name=validated["name"],
                description=validated.get("description"),
                canvas_data=validated.get("canvas_data"),
            )
        except KnowledgePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            KnowledgeSpaceSerializer(knowledge_space).data,
            status=status.HTTP_201_CREATED,
        )


class KnowledgeSpaceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get knowledge space",
        tags=["Knowledge"],
        responses={200: KnowledgeSpaceSerializer},
    )
    def get(self, request, pk=None):
        knowledge_space = _get_knowledge_space_or_404(pk, request.user_id)
        return Response(KnowledgeSpaceSerializer(knowledge_space).data)

    @extend_schema(
        summary="Update knowledge space",
        tags=["Knowledge"],
        request=KnowledgeSpaceUpdateSerializer,
        responses={200: KnowledgeSpaceSerializer},
    )
    def put(self, request, pk=None):
        knowledge_space = _get_knowledge_space_or_404(pk, request.user_id)

        serializer = KnowledgeSpaceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = KnowledgeSpaceService().update_knowledge_space(
                knowledge_space=knowledge_space,
                actor_id=request.user_id,
                updates=serializer.validated_data,
            )
        except KnowledgePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(KnowledgeSpaceSerializer(updated).data)

    @extend_schema(
        summary="Delete knowledge space",
        tags=["Knowledge"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request, pk=None):
        knowledge_space = _get_knowledge_space_or_404(pk, request.user_id)

        try:
            KnowledgeSpaceService().delete_knowledge_space(
                knowledge_space=knowledge_space, actor_id=request.user_id
            )
        except KnowledgePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)


class KnowledgeAssetListCreateView(APIView):
    """
    GET    /knowledge/<uuid:knowledge_pk>/assets/   — list assets
    POST   /knowledge/<uuid:knowledge_pk>/assets/   — upload an asset

    For upload, the request must be multipart/form-data with a `file` field.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post"]

    def _get_space(self, request, knowledge_pk) -> KnowledgeSpace:
        return _get_knowledge_space_or_404(knowledge_pk, request.user_id)

    @extend_schema(
        summary="List assets",
        tags=["Knowledge"],
        responses={200: KnowledgeAssetSerializer(many=True)},
    )
    def get(self, request, knowledge_pk=None):
        knowledge_space = self._get_space(request, knowledge_pk)
        assets = KnowledgeAssetService().list_assets(knowledge_space=knowledge_space)
        return Response(KnowledgeAssetSerializer(assets, many=True).data)

    @extend_schema(
        summary="Upload asset",
        tags=["Knowledge"],
        request=KnowledgeAssetInputSerializer,
        responses={201: KnowledgeAssetSerializer},
    )
    def post(self, request, knowledge_pk=None):
        knowledge_space = self._get_space(request, knowledge_pk)

        serializer = KnowledgeAssetInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_field = serializer.validated_data["file"]

        try:
            asset = KnowledgeAssetService().upload_asset(
                knowledge_space=knowledge_space,
                actor_id=request.user_id,
                file_field=file_field,
            )
        except KnowledgePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(
            KnowledgeAssetSerializer(asset).data,
            status=status.HTTP_201_CREATED,
        )


class KnowledgeAssetDetailView(APIView):
    """
    DELETE /knowledge/<uuid:knowledge_pk>/assets/<uuid:pk>/  — delete an asset
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["delete"]

    @extend_schema(
        summary="Delete asset",
        tags=["Knowledge"],
        responses={204: OpenApiResponse(description="No content")},
    )
    def delete(self, request, knowledge_pk=None, pk=None):
        knowledge_space = _get_knowledge_space_or_404(knowledge_pk, request.user_id)

        try:
            asset_pk = pk if isinstance(pk, uuid.UUID) else uuid.UUID(str(pk))
        except (ValueError, AttributeError) as exc:
            raise NotFound("Asset not found.") from exc

        asset = KnowledgeAsset.objects.filter(
            id=asset_pk, knowledge_space=knowledge_space
        ).first()

        if not asset:
            raise NotFound("Asset not found.")

        try:
            KnowledgeAssetService().delete_asset(
                knowledge_space=knowledge_space,
                asset=asset,
                actor_id=request.user_id,
            )
        except KnowledgePermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        return Response(status=status.HTTP_204_NO_CONTENT)

