import logging
import uuid

from django.db import transaction
from django.db.models import Q, QuerySet

from apps.workspaces.models import Workspace

from .events import KnowledgeEventPublisher
from .models import KnowledgeAsset, KnowledgeSpace
from .storage import KnowledgeAssetStorage

logger = logging.getLogger(__name__)


class KnowledgeSpaceServiceError(Exception):
    pass


class KnowledgePermissionError(KnowledgeSpaceServiceError):
    pass


class KnowledgeSpaceNotFoundError(KnowledgeSpaceServiceError):
    pass


class KnowledgeSpaceService:
    def __init__(self, event_publisher: KnowledgeEventPublisher | None = None):
        self._events = event_publisher or KnowledgeEventPublisher()

    @transaction.atomic
    def create_knowledge_space(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        name: str,
        description: str | None = None,
        canvas_data: dict | None = None,
    ) -> KnowledgeSpace:
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_write:
            raise KnowledgePermissionError(
                "Only workspace members, admins, and owners can create knowledge spaces."
            )

        knowledge_space = KnowledgeSpace.objects.create(
            workspace=workspace,
            name=name,
            description=description,
            canvas_data=canvas_data if canvas_data is not None else {},
            created_by=actor_id,
            updated_by=None,
        )

        logger.info(
            "knowledge_space.created",
            extra={
                "knowledge_space_id": str(knowledge_space.id),
                "workspace_id": str(workspace.id),
                "name": knowledge_space.name,
                "actor_id": str(actor_id),
            },
        )

        _ks = knowledge_space
        _actor = actor_id
        transaction.on_commit(
            lambda: self._events.knowledge_created(knowledge_space=_ks, actor_id=_actor)
        )

        return knowledge_space

    def list_knowledge_spaces(
        self, *, workspace: Workspace, search: str | None = None
    ) -> QuerySet:
        qs = KnowledgeSpace.objects.filter(workspace=workspace)

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        return qs.order_by("-created_at")

    @transaction.atomic
    def update_knowledge_space(
        self, *, knowledge_space: KnowledgeSpace, actor_id: uuid.UUID, updates: dict
    ) -> KnowledgeSpace:
        actor_member = knowledge_space.workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_write:
            raise KnowledgePermissionError(
                "Only workspace members, admins, and owners can update knowledge spaces."
            )

        safe_fields = {"name", "description", "canvas_data"}
        changed = [k for k in updates if k in safe_fields]

        for field in changed:
            setattr(knowledge_space, field, updates[field])

        knowledge_space.updated_by = actor_id
        knowledge_space.save(update_fields=[*changed, "updated_by", "updated_at"])

        logger.info(
            "knowledge_space.updated",
            extra={
                "knowledge_space_id": str(knowledge_space.id),
                "workspace_id": str(knowledge_space.workspace_id),
                "fields": changed,
                "actor_id": str(actor_id),
            },
        )

        _ks = knowledge_space
        _actor = actor_id
        transaction.on_commit(
            lambda: self._events.knowledge_updated(knowledge_space=_ks, actor_id=_actor)
        )

        return knowledge_space

    @transaction.atomic
    def delete_knowledge_space(
        self, *, knowledge_space: KnowledgeSpace, actor_id: uuid.UUID
    ) -> None:
        actor_member = knowledge_space.workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise KnowledgePermissionError(
                "Only workspace admins and owners can delete knowledge spaces."
            )

        knowledge_space.delete()

        logger.info(
            "knowledge_space.deleted",
            extra={
                "knowledge_space_id": str(knowledge_space.id),
                "workspace_id": str(knowledge_space.workspace_id),
                "actor_id": str(actor_id),
            },
        )

        _ks = knowledge_space
        _actor = actor_id
        transaction.on_commit(
            lambda: self._events.knowledge_deleted(knowledge_space=_ks, actor_id=_actor)
        )


class KnowledgeAssetService:
    """
    Handles KnowledgeAsset lifecycle: upload, list, delete.
    """

    def __init__(
        self,
        storage: KnowledgeAssetStorage | None = None,
        event_publisher: KnowledgeEventPublisher | None = None,
    ):
        self._storage = storage or KnowledgeAssetStorage()
        self._events = event_publisher or KnowledgeEventPublisher()

    @transaction.atomic
    def upload_asset(
        self,
        *,
        knowledge_space: KnowledgeSpace,
        actor_id: uuid.UUID,
        file_field,
    ) -> KnowledgeAsset:
        """
        Save an uploaded file, create a KnowledgeAsset record.

        Business rules:
          - Actor must have can_write role on the workspace
        """
        actor_member = knowledge_space.workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_write:
            raise KnowledgePermissionError(
                "Only workspace members can upload assets."
            )

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

        logger.info(
            "knowledge_asset.created",
            extra={
                "asset_id": str(asset.id),
                "knowledge_space_id": str(knowledge_space.id),
                "file_name": original_name,
                "file_type": file_type,
                "size": file_size,
                "actor_id": str(actor_id),
            },
        )

        return asset

    def list_assets(
        self, *, knowledge_space: KnowledgeSpace
    ) -> QuerySet:
        """Return all assets for a knowledge space, newest first."""
        return KnowledgeAsset.objects.filter(
            knowledge_space=knowledge_space
        ).order_by("-created_at")

    @transaction.atomic
    def delete_asset(
        self,
        *,
        knowledge_space: KnowledgeSpace,
        asset: KnowledgeAsset,
        actor_id: uuid.UUID,
    ) -> None:
        """
        Delete an asset: remove file from storage, then soft-delete the record.

        Business rules:
          - Actor must have can_write role
        """
        actor_member = knowledge_space.workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_write:
            raise KnowledgePermissionError(
                "Only workspace members can delete assets."
            )

        self._storage.delete(asset.storage_key)
        asset.delete()

        logger.info(
            "knowledge_asset.deleted",
            extra={
                "asset_id": str(asset.id),
                "storage_key": asset.storage_key,
                "knowledge_space_id": str(knowledge_space.id),
                "actor_id": str(actor_id),
            },
        )

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
