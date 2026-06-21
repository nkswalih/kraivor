import uuid
from typing import Any

from django.db import transaction
from django.db.models import QuerySet

from ..events import KnowledgeEventPublisher
from ..models import KnowledgeAsset, KnowledgeSpace
from ..storage import KnowledgeAssetStorage
from .base import KnowledgePermissionError

logger = __import__("logging").getLogger(__name__)


class KnowledgeAssetService:
    def __init__(
        self,
        storage: KnowledgeAssetStorage | None = None,
        event_publisher: KnowledgeEventPublisher | None = None,
    ) -> None:
        self._storage = storage or KnowledgeAssetStorage()
        self._events = event_publisher or KnowledgeEventPublisher()

    @transaction.atomic
    def upload_asset(
        self,
        *,
        knowledge_space: KnowledgeSpace,
        actor_id: uuid.UUID,
        file_field: Any,  # noqa: ANN401
    ) -> KnowledgeAsset:
        actor_member = knowledge_space.workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_write:
            raise KnowledgePermissionError("Only workspace members can upload assets.")
        storage_key, file_size, mime_type, url = self._storage.save(
            knowledge_space.id, file_field
        )
        original_name = file_field.name
        file_type = self._classify_mime(mime_type)
        asset = KnowledgeAsset.objects.create(
            knowledge_space=knowledge_space,
            file_name=original_name,
            file_size=file_size,
            file_type=file_type,
            mime_type=mime_type,
            storage_key=storage_key,
            url=url,
            uploaded_by=actor_id,
            metadata={},
        )
        return asset

    def get_asset(
        self, *, knowledge_space: KnowledgeSpace, asset_id: uuid.UUID
    ) -> KnowledgeAsset | None:
        return KnowledgeAsset.objects.filter(
            knowledge_space=knowledge_space, id=asset_id
        ).first()

    def list_assets(self, *, knowledge_space: KnowledgeSpace) -> QuerySet:
        return KnowledgeAsset.objects.filter(knowledge_space=knowledge_space).order_by(
            "-created_at"
        )

    @transaction.atomic
    def delete_asset(
        self,
        *,
        knowledge_space: KnowledgeSpace,
        asset: KnowledgeAsset,
        actor_id: uuid.UUID,
    ) -> None:
        actor_member = knowledge_space.workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_write:
            raise KnowledgePermissionError("Only workspace members can delete assets.")
        self._storage.delete(asset.storage_key)
        asset.delete()

    @staticmethod
    def _classify_mime(mime_type: str) -> str:
        major = mime_type.split("/")[0]
        if major == "image":
            return "image"
        if mime_type == "application/pdf":
            return "pdf"
        if major == "text" or mime_type in {
            "application/json",
            "application/javascript",
        }:
            return "code"
        return "file"
