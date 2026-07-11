import logging
import uuid
from django.db import transaction
from django.utils import timezone

from ..constants import PLAN_LIMITS, WorkspacePlan, WorkspaceRole
from ..events import WorkspaceEventPublisher
from ..models import Workspace, WorkspaceMember

logger = logging.getLogger(__name__)


class WorkspaceServiceError(Exception):
    """Base exception for all workspace service errors."""


class WorkspacePermissionError(WorkspaceServiceError):
    """User lacks permission for the requested operation."""


class WorkspaceLimitError(WorkspaceServiceError):
    """Plan limit would be exceeded."""


class WorkspaceNotFoundError(WorkspaceServiceError):
    """Resource not found or not accessible to the requesting user."""


class WorkspaceService:
    def __init__(self, event_publisher: WorkspaceEventPublisher | None = None) -> None:
        self._events = event_publisher or WorkspaceEventPublisher()

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
        workspace = Workspace.objects.create(
            owner_id=owner_id,
            name=name,
            slug=slug,
            avatar_url=avatar_url,
            description=description,
            settings=settings or {},
            plan=WorkspacePlan.FREE,
        )
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
                "slug": workspace.slug,
                "owner_id": str(owner_id),
            },
        )
        self._events.workspace_created(workspace=workspace, actor_id=owner_id)
        return workspace

    def update_workspace(
        self, *, workspace: Workspace, actor_id: uuid.UUID, updates: dict
    ) -> Workspace:
        member = workspace.get_member(actor_id)
        if not member or not member.can_admin:
            raise WorkspacePermissionError(
                "Only workspace admins and owners can update settings."
            )
        safe_fields = {"name", "avatar_url", "description", "settings"}
        for field, value in updates.items():
            if field in safe_fields:
                setattr(workspace, field, value)
        workspace.save(
            update_fields=[*[k for k in updates if k in safe_fields], "updated_at"]
        )
        logger.info(
            "workspace.updated",
            extra={"workspace_id": str(workspace.id), "fields": list(updates.keys())},
        )
        return workspace

    @transaction.atomic
    def delete_workspace(self, *, workspace: Workspace, actor_id: uuid.UUID) -> None:
        if not workspace.is_owner(actor_id):
            raise WorkspacePermissionError(
                "Only the workspace owner can delete the workspace."
            )
        workspace.members.filter(deleted_at__isnull=True).update(
            deleted_at=timezone.now()
        )
        workspace.delete()
        logger.info(
            "workspace.deleted",
            extra={"workspace_id": str(workspace.id), "actor_id": str(actor_id)},
        )
        self._events.workspace_deleted(workspace=workspace, actor_id=actor_id)

    def update_member_role(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_role: str,
    ) -> WorkspaceMember:
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
        if (
            target_member.role == WorkspaceRole.ADMIN
            and actor_member.role != WorkspaceRole.OWNER
        ):
            raise WorkspacePermissionError("Only the owner can change an admin's role.")
        old_role = target_member.role
        target_member.role = new_role
        target_member.save(update_fields=["role", "updated_at"])
        logger.info(
            "workspace.member.role_changed",
            extra={
                "workspace_id": str(workspace.id),
                "user_id": str(target_user_id),
                "old_role": old_role,
                "new_role": new_role,
                "actor_id": str(actor_id),
            },
        )
        self._events.member_role_changed(
            workspace=workspace,
            member=target_member,
            old_role=old_role,
            new_role=new_role,
            actor_id=actor_id,
        )
        return target_member

    def remove_member(
        self, *, workspace: Workspace, actor_id: uuid.UUID, target_user_id: uuid.UUID
    ) -> None:
        target_member = workspace.get_member(target_user_id)
        if not target_member:
            raise WorkspaceNotFoundError(f"User {target_user_id} is not a member.")
        if target_member.is_owner:
            raise WorkspacePermissionError(
                "The owner cannot be removed. Transfer ownership first."
            )
        reason = "removed_by_admin"
        if actor_id == target_user_id:
            reason = "left"
        else:
            actor_member = workspace.get_member(actor_id)
            if not actor_member or not actor_member.can_admin:
                raise WorkspacePermissionError(
                    "Only admins and owners can remove members."
                )
            if (
                target_member.role == WorkspaceRole.ADMIN
                and actor_member.role != WorkspaceRole.OWNER
            ):
                raise WorkspacePermissionError("Only the owner can remove admins.")
        target_member.delete()
        logger.info(
            "workspace.member.removed",
            extra={
                "workspace_id": str(workspace.id),
                "user_id": str(target_user_id),
                "actor_id": str(actor_id),
                "reason": reason,
            },
        )
        self._events.member_removed(
            workspace=workspace,
            user_id=target_user_id,
            actor_id=actor_id,
            reason=reason,
        )
        _ws_id = str(workspace.id)
        _uid = str(target_user_id)
        _aid = str(actor_id)
        _reason = reason
        transaction.on_commit(
            lambda: _dispatch_member_removed_notification(
                workspace_id=_ws_id, removed_user_id=_uid, actor_id=_aid, reason=_reason
            )
        )

    def _check_member_limit(self, workspace: Workspace) -> None:
        limits = PLAN_LIMITS.get(workspace.plan, {})
        max_members = limits.get("max_members", -1)
        if max_members == -1:
            return
        if workspace.members.count() >= max_members:
            raise WorkspaceLimitError(
                f"Your {workspace.plan} plan allows a maximum of {max_members} members. "
                "Upgrade to add more."
            )

    @transaction.atomic
    def add_member(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str = WorkspaceRole.MEMBER,
    ) -> WorkspaceMember:
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise WorkspacePermissionError(
                "Only admins and owners can add workspace members."
            )
        if role == WorkspaceRole.OWNER:
            raise WorkspacePermissionError("Cannot assign owner role directly.")
        self._check_member_limit(workspace)
        existing = WorkspaceMember.all_objects.filter(
            workspace=workspace, user_id=user_id
        ).first()
        if existing and not existing.is_deleted:
            raise WorkspaceServiceError(f"User {user_id} is already a member.")
        if existing and existing.is_deleted:
            existing.role = role
            existing.deleted_at = None
            existing.joined_at = timezone.now()
            existing.invited_by_id = actor_id
            existing.save(
                update_fields=[
                    "role",
                    "deleted_at",
                    "joined_at",
                    "invited_by_id",
                    "updated_at",
                ]
            )
            member = existing
        else:
            member = WorkspaceMember.objects.create(
                workspace=workspace,
                user_id=user_id,
                role=role,
                joined_at=timezone.now(),
                invited_by_id=actor_id,
            )
        self._events.member_added(workspace=workspace, member=member, actor_id=actor_id)
        return member


def _dispatch_member_joined_notification(
    workspace_id: str, user_id: str, role: str
) -> None:
    try:
        from ..tasks import notify_member_joined

        notify_member_joined.delay(
            workspace_id=workspace_id, user_id=user_id, role=role
        )
    except Exception as exc:
        logger.error(
            "task.dispatch.member_joined.failed",
            extra={"workspace_id": workspace_id, "user_id": user_id, "error": str(exc)},
        )


def _dispatch_member_removed_notification(
    workspace_id: str, removed_user_id: str, actor_id: str, reason: str
) -> None:
    try:
        from ..tasks import notify_member_removed

        notify_member_removed.delay(
            workspace_id=workspace_id,
            removed_user_id=removed_user_id,
            actor_id=actor_id,
            reason=reason,
        )
    except Exception as exc:
        logger.error(
            "task.dispatch.member_removed.failed",
            extra={
                "workspace_id": workspace_id,
                "removed_user_id": removed_user_id,
                "error": str(exc),
            },
        )
