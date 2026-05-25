"""
Workspace service layer.

All business logic lives here, not in views or models.
Views call services. Services call models and external clients.
This makes logic testable without HTTP and reusable across views.

Key responsibilities:
  - Enforce business rules (e.g. owner cannot be removed)
  - Emit domain events to Kafka after state changes
  - Keep workspace + member creation atomic (DB transaction)
  - Enforce plan limits before creating resources
"""

import logging
import uuid

from django.db import transaction
from django.utils import timezone

from .constants import PLAN_LIMITS, WorkspacePlan, WorkspaceRole
from .events import WorkspaceEventPublisher
from .models import Workspace, WorkspaceMember

logger = logging.getLogger(__name__)


class WorkspaceServiceError(Exception):
    """Base exception for workspace service errors."""
    pass


class WorkspacePermissionError(WorkspaceServiceError):
    """Raised when a user lacks permission for an operation."""
    pass


class WorkspaceLimitError(WorkspaceServiceError):
    """Raised when a plan limit would be exceeded."""
    pass


class WorkspaceNotFoundError(WorkspaceServiceError):
    """Raised when a workspace is not found or not accessible."""
    pass


class WorkspaceService:
    """
    Stateless service class for workspace operations.
    Instantiate per-request (no shared mutable state).
    """

    def __init__(self, event_publisher: WorkspaceEventPublisher | None = None):
        # Allow dependency injection for testing — default to real publisher
        self._events = event_publisher or WorkspaceEventPublisher()

    # ─── Workspace CRUD ───────────────────────────────────────────────────────

    @transaction.atomic
    def create_workspace(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        slug: str,
        avatar_url: str | None = None,
        description: str | None = None,
        settings: dict | None = None,
    ) -> Workspace:
        """
        Create a workspace and add the creator as owner in one atomic transaction.

        The workspace and owner membership must be created together —
        a workspace without an owner is an inconsistent state.
        """
        workspace = Workspace.objects.create(
            owner_id=owner_id,
            name=name,
            slug=slug,
            avatar_url=avatar_url,
            description=description,
            settings=settings or {},
            plan=WorkspacePlan.FREE,
        )

        # Add creator as owner member — this is the only way to get owner role
        WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=owner_id,
            role=WorkspaceRole.OWNER,
            joined_at=timezone.now(),
        )

        logger.info(
            "workspace.created",
            extra={
                "workspace_id": str(workspace.id),
                "workspace_slug": workspace.slug,
                "owner_id": str(owner_id),
            },
        )

        # Publish event — consumed by Notifications (welcome), Analytics
        self._events.workspace_created(workspace=workspace, actor_id=owner_id)

        return workspace

    def update_workspace(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        updates: dict,
    ) -> Workspace:
        """
        Update workspace fields. Requires admin or owner role.
        Slug, owner_id, plan are not updatable via this method.
        """
        member = workspace.get_member(actor_id)
        if not member or not member.can_admin:
            raise WorkspacePermissionError(
                "Only workspace admins and owners can update workspace settings."
            )

        safe_fields = {"name", "avatar_url", "description", "settings"}
        for field, value in updates.items():
            if field in safe_fields:
                setattr(workspace, field, value)

        workspace.save(update_fields=[*updates.keys(), "updated_at"])

        logger.info(
            "workspace.updated",
            extra={
                "workspace_id": str(workspace.id),
                "actor_id": str(actor_id),
                "fields": list(updates.keys()),
            },
        )

        return workspace

    @transaction.atomic
    def delete_workspace(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
    ) -> None:
        """
        Soft-delete a workspace. Only the owner can delete.

        Cascades: all workspace members are also soft-deleted in this transaction.
        Other resources (repos, notes, analyses) are cascade-deleted asynchronously
        via the workspace.deleted Kafka event consumed by each service.
        """
        if not workspace.is_owner(actor_id):
            raise WorkspacePermissionError(
                "Only the workspace owner can delete the workspace."
            )

        # Soft delete all members first (maintains referential consistency)
        workspace.members.all().alive().update(deleted_at=timezone.now())

        # Soft delete the workspace
        workspace.delete()

        logger.info(
            "workspace.deleted",
            extra={
                "workspace_id": str(workspace.id),
                "actor_id": str(actor_id),
            },
        )

        self._events.workspace_deleted(workspace=workspace, actor_id=actor_id)

    # ─── Member Management ────────────────────────────────────────────────────

    @transaction.atomic
    def add_member(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = WorkspaceRole.MEMBER,
    ) -> WorkspaceMember:
        """
        Add a user to the workspace. Requires admin role.
        Cannot add a user who is already a member (including soft-deleted).
        """
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise WorkspacePermissionError(
                "Only admins and owners can add workspace members."
            )

        if role == WorkspaceRole.OWNER:
            raise WorkspacePermissionError(
                "Cannot assign owner role directly. Use transfer_ownership()."
            )

        # Enforce plan member limits
        self._check_member_limit(workspace)

        # Check for existing (including soft-deleted) — no reuse of soft-deleted records
        existing = WorkspaceMember.all_objects.filter(
            workspace=workspace, user_id=user_id
        ).first()
        if existing and not existing.is_deleted:
            raise WorkspaceServiceError(f"User {user_id} is already a member.")
        if existing and existing.is_deleted:
            # Restore the member record (cleaner than creating a new row)
            existing.role = role
            existing.deleted_at = None
            existing.joined_at = timezone.now()
            existing.invited_by_id = actor_id
            existing.save(update_fields=["role", "deleted_at", "joined_at", "invited_by_id", "updated_at"])
            member = existing
        else:
            member = WorkspaceMember.objects.create(
                workspace=workspace,
                user_id=user_id,
                role=role,
                joined_at=timezone.now(),
                invited_by_id=actor_id,
            )

        logger.info(
            "workspace.member.added",
            extra={
                "workspace_id": str(workspace.id),
                "user_id": str(user_id),
                "role": role,
                "actor_id": str(actor_id),
            },
        )

        self._events.member_added(workspace=workspace, member=member, actor_id=actor_id)

        return member

    def update_member_role(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: str,
    ) -> WorkspaceMember:
        """
        Change a member's role. Requires admin role.
        Cannot change the owner's role. Cannot promote to owner.
        """
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise WorkspacePermissionError(
                "Only admins and owners can change member roles."
            )

        if new_role == WorkspaceRole.OWNER:
            raise WorkspacePermissionError(
                "Cannot assign owner role via role update. Use transfer_ownership()."
            )

        target_member = workspace.get_member(target_user_id)
        if not target_member:
            raise WorkspaceNotFoundError(f"User {target_user_id} is not a member.")

        if target_member.is_owner:
            raise WorkspacePermissionError("Cannot change the owner's role.")

        # Admin cannot change another admin's role (only owner can)
        if target_member.role == WorkspaceRole.ADMIN and actor_member.role != WorkspaceRole.OWNER:
            raise WorkspacePermissionError("Only the owner can change an admin's role.")

        target_member.role = new_role
        target_member.save(update_fields=["role", "updated_at"])

        return target_member

    def remove_member(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        """
        Remove a member from the workspace.
        - Admins can remove members and viewers.
        - Only the owner can remove admins.
        - The owner cannot be removed.
        - A member can remove themselves (leave).
        """
        target_member = workspace.get_member(target_user_id)
        if not target_member:
            raise WorkspaceNotFoundError(f"User {target_user_id} is not a member.")

        if target_member.is_owner:
            raise WorkspacePermissionError(
                "The owner cannot be removed. Transfer ownership first."
            )

        # Self-removal (leaving) is always allowed for non-owners
        if actor_id == target_user_id:
            target_member.delete()
            return

        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise WorkspacePermissionError(
                "Only admins and owners can remove members."
            )

        if target_member.role == WorkspaceRole.ADMIN and actor_member.role != WorkspaceRole.OWNER:
            raise WorkspacePermissionError("Only the owner can remove admins.")

        target_member.delete()

        logger.info(
            "workspace.member.removed",
            extra={
                "workspace_id": str(workspace.id),
                "user_id": str(target_user_id),
                "actor_id": str(actor_id),
            },
        )

    # ─── Plan Enforcement ─────────────────────────────────────────────────────

    def _check_member_limit(self, workspace: Workspace) -> None:
        limits = PLAN_LIMITS.get(workspace.plan, {})
        max_members = limits.get("max_members", -1)
        if max_members == -1:
            return  # unlimited
        current_count = workspace.members.count()
        if current_count >= max_members:
            raise WorkspaceLimitError(
                f"Your {workspace.plan} plan allows a maximum of {max_members} members. "
                "Upgrade your plan to add more members."
            )