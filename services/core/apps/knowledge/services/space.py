import uuid

from django.db import transaction
from django.db.models import Q, QuerySet

from apps.workspaces.models import Workspace

from ..events import KnowledgeEventPublisher
from ..models import KnowledgeSpace
from .base import KnowledgePermissionError

logger = __import__("logging").getLogger(__name__)


class KnowledgeSpaceService:
    def __init__(self, event_publisher: KnowledgeEventPublisher | None = None) -> None:
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
        _ks = knowledge_space
        _actor = actor_id
        transaction.on_commit(
            lambda: self._events.knowledge_deleted(knowledge_space=_ks, actor_id=_actor)
        )
