from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.permissions import IsAuthenticated

from ..serializers import KnowledgeAssetInputSerializer, KnowledgeAssetSerializer
from ..services import KnowledgeAssetService
from .spaces import _get_space_or_404


@extend_schema(tags=["Knowledge"])
class KnowledgeAssetListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List knowledge assets",
        responses={200: KnowledgeAssetSerializer(many=True)},
    )
    def get(self, request: Request, knowledge_pk: str | None = None) -> Response:
        space = _get_space_or_404(knowledge_pk, request.user_id)
        assets = KnowledgeAssetService().list_assets(knowledge_space=space)
        return Response(KnowledgeAssetSerializer(assets, many=True).data)

    @extend_schema(
        summary="Upload knowledge asset",
        request=KnowledgeAssetInputSerializer,
        responses={201: KnowledgeAssetSerializer},
    )
    def post(self, request: Request, knowledge_pk: str | None = None) -> Response:
        space = _get_space_or_404(knowledge_pk, request.user_id)
        serializer = KnowledgeAssetInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = KnowledgeAssetService().upload_asset(
            knowledge_space=space,
            actor_id=request.user_id,
            file_field=serializer.validated_data["file"],
        )
        return Response(
            KnowledgeAssetSerializer(asset).data, status=status.HTTP_201_CREATED
        )


@extend_schema(tags=["Knowledge"])
class KnowledgeAssetDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get knowledge asset", responses={200: KnowledgeAssetSerializer}
    )
    def get(
        self, request: Request, knowledge_pk: str | None = None, pk: str | None = None
    ) -> Response:
        space = _get_space_or_404(knowledge_pk, request.user_id)
        asset = KnowledgeAssetService().get_asset(knowledge_space=space, asset_id=pk)
        if not asset:
            raise NotFound("Asset not found.")
        return Response(KnowledgeAssetSerializer(asset).data)

    @extend_schema(summary="Delete knowledge asset", responses={204: None})
    def delete(
        self, request: Request, knowledge_pk: str | None = None, pk: str | None = None
    ) -> Response:
        space = _get_space_or_404(knowledge_pk, request.user_id)
        asset = KnowledgeAssetService().get_asset(knowledge_space=space, asset_id=pk)
        if not asset:
            raise NotFound("Asset not found.")
        KnowledgeAssetService().delete_asset(
            knowledge_space=space, asset=asset, actor_id=request.user_id
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
