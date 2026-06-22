import uuid
from django.db.models import Prefetch, Q, QuerySet

from apps.knowledge.models import KnowledgeAsset, KnowledgeSpace
from core.cache import CacheService


class KnowledgeSpaceSelector:
    @staticmethod
    def list_for_workspace(workspace_id: uuid.UUID, search: str | None = None) -> QuerySet[KnowledgeSpace]:
        qs = KnowledgeSpace.objects.filter(
            workspace_id=workspace_id, deleted_at__isnull=True
        ).select_related("workspace")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return qs.order_by("-updated_at")

    @staticmethod
    def get_detail(space_id: uuid.UUID) -> KnowledgeSpace | None:
        return (
            KnowledgeSpace.objects.select_related("workspace")
            .prefetch_related(
                Prefetch(
                    "assets",
                    queryset=KnowledgeAsset.objects.filter(deleted_at__isnull=True),
                )
            )
            .filter(id=space_id, deleted_at__isnull=True)
            .first()
        )

    @staticmethod
    def get_asset_count(space_id: uuid.UUID) -> int:
        key = f"ks:asset_count:{space_id}"
        return CacheService.get_or_set(
            key=key,
            timeout=60,
            fallback=lambda: KnowledgeAsset.objects.filter(
                knowledge_space_id=space_id, deleted_at__isnull=True
            ).count(),
        )


class KnowledgeAssetSelector:
    @staticmethod
    def list_for_space(space_id: uuid.UUID) -> QuerySet[KnowledgeAsset]:
        return KnowledgeAsset.objects.filter(
            knowledge_space_id=space_id, deleted_at__isnull=True
        ).order_by("-created_at")

    @staticmethod
    def get_detail(asset_id: uuid.UUID, space_id: uuid.UUID) -> KnowledgeAsset | None:
        return KnowledgeAsset.objects.select_related("knowledge_space").filter(
            id=asset_id, knowledge_space_id=space_id, deleted_at__isnull=True
        ).first()
