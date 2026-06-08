"""
Knowledge Space service layer — KRV-022 (Knowledge Workspace / Infinite Canvas).

All business logic lives here — views are thin HTTP adapters.

Service contract:
  - Receives validated data from serializers
  - Enforces role-based permissions (create/update → can_write; delete → can_admin)
  - Runs DB mutations inside transactions
  - Publishes Kafka events AFTER successful DB commit via transaction.on_commit
  - Raises typed exceptions that views translate to HTTP responses

Permission model:
  List / Retrieve  — any active workspace member (owner, admin, member, viewer)
  Create / Update  — can_write: owner, admin, member  (not viewer)
  Delete           — can_admin: owner, admin only

Search:
  list_knowledge_spaces() accepts an optional `search` string that filters
  across name (case-insensitive) and description (case-insensitive) using
  a Q OR query — same DB-level search used across the platform.
"""

import logging
import uuid

from django.db import transaction
from django.db.models import Q, QuerySet

from apps.workspaces.models import Workspace

from .events import KnowledgeEventPublisher
from .models import KnowledgeSpace

logger = logging.getLogger(__name__)


# ─── Exception hierarchy ──────────────────────────────────────────────────────


class KnowledgeSpaceServiceError(Exception):
    """Base exception for all knowledge space service errors."""

    pass


class KnowledgePermissionError(KnowledgeSpaceServiceError):
    """User lacks permission for the requested operation."""

    pass


class KnowledgeSpaceNotFoundError(KnowledgeSpaceServiceError):
    """Knowledge space not found or not accessible to the requesting user."""

    pass


# ─── Knowledge Space Service ──────────────────────────────────────────────────


class KnowledgeSpaceService:
    """
    Handles the knowledge space lifecycle: create, list, update, delete.
    Instantiate per-request. No shared mutable state.
    """

    def __init__(self, event_publisher: KnowledgeEventPublisher | None = None):
        self._events = event_publisher or KnowledgeEventPublisher()

    # ── Create ────────────────────────────────────────────────────────────────

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
        """
        Create a new knowledge space (infinite canvas) inside a workspace.

        Business rules:
          - Actor must have can_write role (owner, admin, or member)
          - Viewers cannot create knowledge spaces
          - canvas_data defaults to an empty dict when not provided
          - created_by is set to actor_id; updated_by remains None until first update

        Raises:
            KnowledgePermissionError — actor is a viewer or not a member
        """
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
            lambda: self._events.knowledge_created(
                knowledge_space=_ks,
                actor_id=_actor,
            )
        )

        return knowledge_space

    # ── List ──────────────────────────────────────────────────────────────────

    def list_knowledge_spaces(
        self,
        *,
        workspace: Workspace,
        search: str | None = None,
    ) -> QuerySet:
        """
        Return all active (non-deleted) knowledge spaces for a workspace.

        Any active workspace member may list knowledge spaces — membership
        is enforced at the view layer via _get_workspace_or_404().

        search: optional string that filters across name and description
                using case-insensitive containment (icontains). Matches
                either field (OR semantics).

        Ordered newest-first to match other list endpoints in the service.
        """
        qs = KnowledgeSpace.objects.filter(workspace=workspace)

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        return qs.order_by("-created_at")

    # ── Update ────────────────────────────────────────────────────────────────

    @transaction.atomic
    def update_knowledge_space(
        self,
        *,
        knowledge_space: KnowledgeSpace,
        actor_id: uuid.UUID,
        updates: dict,
    ) -> KnowledgeSpace:
        """
        Update a knowledge space's name, description, and/or canvas_data.

        Follows the same safe-fields pattern as WorkspaceService.update_workspace():
        only fields in `safe_fields` are applied, preventing unexpected overwrites.

        updated_by is always set to actor_id on every successful update.

        Business rules:
          - Actor must have can_write role (owner, admin, or member)
          - Viewers cannot update knowledge spaces
          - canvas_data is treated as a full replacement when provided
            (the frontend sends the entire canvas state each time)
          - Fields absent from `updates` are not modified

        Raises:
            KnowledgePermissionError — actor is a viewer or not a member
        """
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
            lambda: self._events.knowledge_updated(
                knowledge_space=_ks,
                actor_id=_actor,
            )
        )

        return knowledge_space

    # ── Delete ────────────────────────────────────────────────────────────────

    @transaction.atomic
    def delete_knowledge_space(
        self,
        *,
        knowledge_space: KnowledgeSpace,
        actor_id: uuid.UUID,
    ) -> None:
        """
        Soft-delete a knowledge space.

        TimestampedModel.delete() sets deleted_at on both the DB row and the
        in-memory Python instance — no refresh_from_db() needed after this call.

        Business rules:
          - Only admins and owners can delete knowledge spaces (can_admin)
          - Members and viewers cannot delete

        Raises:
            KnowledgePermissionError — actor does not have admin/owner role
        """
        actor_member = knowledge_space.workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise KnowledgePermissionError(
                "Only workspace admins and owners can delete knowledge spaces."
            )

        knowledge_space.delete()  # soft-delete; mutates deleted_at on in-memory instance

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
            lambda: self._events.knowledge_deleted(
                knowledge_space=_ks,
                actor_id=_actor,
            )
        )
