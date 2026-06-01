"""
Workspace service layer — KRV-019 (workspace CRUD) + KRV-020 (invitations).

All business logic lives here — views are thin HTTP adapters.

Service contract:
  - Receives validated data from serializers
  - Enforces business rules (permissions, plan limits, role transitions)
  - Runs DB mutations inside transactions
  - Publishes Kafka events AFTER successful DB commit
  - Dispatches Celery tasks for async side-effects (email, notifications)
  - Raises typed exceptions that views translate to HTTP responses

KRV-020 additions:
  InvitationService — invite, accept, revoke, list
"""

import logging
import uuid

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from .constants import PLAN_LIMITS, WorkspacePlan, WorkspaceRole
from .events import WorkspaceEventPublisher
from .models import Workspace, WorkspaceInvitation, WorkspaceMember

logger = logging.getLogger(__name__)


# ─── Exception hierarchy ───────────────────────────────────────────────────────

class WorkspaceServiceError(Exception):
    """Base exception for all workspace service errors."""
    pass


class WorkspacePermissionError(WorkspaceServiceError):
    """User lacks permission for the requested operation."""
    pass


class WorkspaceLimitError(WorkspaceServiceError):
    """Plan limit would be exceeded."""
    pass


class WorkspaceNotFoundError(WorkspaceServiceError):
    """Resource not found or not accessible to the requesting user."""
    pass


class InvitationError(WorkspaceServiceError):
    """Invalid invitation state (expired, already accepted, duplicate)."""
    pass


# ─── Workspace Service (KRV-019) ──────────────────────────────────────────────

class WorkspaceService:
    """
    Handles workspace lifecycle: create, update, delete.
    Instantiate per-request. No shared mutable state.
    """

    def __init__(self, event_publisher: WorkspaceEventPublisher | None = None):
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
        """
        Create workspace + owner membership in one atomic transaction.
        A workspace without an owner is an inconsistent state — both are created together.
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
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        updates: dict,
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

        workspace.save(update_fields=[*[k for k in updates if k in safe_fields], "updated_at"])
        logger.info("workspace.updated", extra={"workspace_id": str(workspace.id), "fields": list(updates.keys())})
        return workspace

    @transaction.atomic
    def delete_workspace(self, *, workspace: Workspace, actor_id: uuid.UUID) -> None:
        if not workspace.is_owner(actor_id):
            raise WorkspacePermissionError("Only the workspace owner can delete the workspace.")

        workspace.members.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
        workspace.delete()

        logger.info("workspace.deleted", extra={"workspace_id": str(workspace.id), "actor_id": str(actor_id)})
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
            raise WorkspacePermissionError("Only admins and owners can change member roles.")

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
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        target_user_id: uuid.UUID,
    ) -> None:
        target_member = workspace.get_member(target_user_id)
        if not target_member:
            raise WorkspaceNotFoundError(f"User {target_user_id} is not a member.")

        if target_member.is_owner:
            raise WorkspacePermissionError(
                "The owner cannot be removed. Transfer ownership first."
            )

        # Self-removal (leaving) — always allowed for non-owners
        reason = "removed_by_admin"
        if actor_id == target_user_id:
            reason = "left"
        else:
            actor_member = workspace.get_member(actor_id)
            if not actor_member or not actor_member.can_admin:
                raise WorkspacePermissionError("Only admins and owners can remove members.")
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

        # Async notification — dispatched via transaction.on_commit so the task
        # only fires after the DB commit succeeds and the broker is reachable.
        # This also means the task is never dispatched in unit tests that don't
        # wrap in a real transaction (on_commit fires immediately in those cases
        # but the lambda is caught by _dispatch_member_removed which swallows errors).
        _ws_id = str(workspace.id)
        _uid = str(target_user_id)
        _aid = str(actor_id)
        _reason = reason
        transaction.on_commit(
            lambda: _dispatch_member_removed_notification(
                workspace_id=_ws_id,
                removed_user_id=_uid,
                actor_id=_aid,
                reason=_reason,
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

    # Kept for backward compat with KRV-019 views
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
            raise WorkspacePermissionError("Only admins and owners can add workspace members.")
        if role == WorkspaceRole.OWNER:
            raise WorkspacePermissionError("Cannot assign owner role directly.")
        self._check_member_limit(workspace)

        existing = WorkspaceMember.all_objects.filter(workspace=workspace, user_id=user_id).first()
        if existing and not existing.is_deleted:
            raise WorkspaceServiceError(f"User {user_id} is already a member.")
        if existing and existing.is_deleted:
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

        self._events.member_added(workspace=workspace, member=member, actor_id=actor_id)
        return member


# ─── Invitation Service (KRV-020) ─────────────────────────────────────────────

class InvitationService:
    """
    Handles the full invitation lifecycle:
      create_invitation → (email sent async) → accept_invitation → member created
                                              → revoke_invitation  (admin action)

    Instantiate per-request. No shared state.
    """

    def __init__(self, event_publisher: WorkspaceEventPublisher | None = None):
        self._events = event_publisher or WorkspaceEventPublisher()

    @transaction.atomic
    def create_invitation(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        actor_name: str,
        email: str,
        role: str = WorkspaceRole.MEMBER,
    ) -> WorkspaceInvitation:
        """
        Create a pending invitation and dispatch the invitation email async.

        Business rules:
          - Only admin/owner can invite
          - Cannot invite an existing active member
          - Cannot create a duplicate pending invitation for the same email
          - Cannot assign owner role via invitation
          - Plan member limit checked against current + pending invitations

        The invitation email is sent by a Celery task (not in this transaction)
        so that email delivery failures don't roll back the invitation creation.
        """
        # ── Permission check ─────────────────────────────────────────────────
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise WorkspacePermissionError(
                "Only workspace admins and owners can invite members."
            )

        # ── Role validation ───────────────────────────────────────────────────
        if role == WorkspaceRole.OWNER:
            raise WorkspacePermissionError(
                "Cannot invite someone as an owner. Transfer ownership after they join."
            )

        # ── Duplicate member check ────────────────────────────────────────────
        # Check if the email belongs to an existing member.
        # We don't have email→user_id mapping in core service (that's identity).
        # This check is best-effort: we check the invitation table for email collision.
        # The accept flow does a definitive user_id check.
        existing_pending = (
            WorkspaceInvitation.objects
            .filter(
                workspace=workspace,
                email=email,
                accepted_at__isnull=True,
                deleted_at__isnull=True,
            )
            .filter(expires_at__gt=timezone.now())
            .first()
        )
        if existing_pending:
            raise InvitationError(
                f"A pending invitation already exists for {email}. "
                "Revoke it before sending a new one, or wait for it to expire."
            )

        # ── Plan limit check ─────────────────────────────────────────────────
        # Count current members + pending (non-expired) invitations
        limits = PLAN_LIMITS.get(workspace.plan, {})
        max_members = limits.get("max_members", -1)
        if max_members != -1:
            current = workspace.members.count()
            pending_invites = WorkspaceInvitation.objects.filter(
                workspace=workspace,
                accepted_at__isnull=True,
                deleted_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).count()
            if current + pending_invites >= max_members:
                raise WorkspaceLimitError(
                    f"Your {workspace.plan} plan allows a maximum of {max_members} members "
                    f"(including pending invitations). Upgrade to invite more."
                )

        # ── Create invitation ─────────────────────────────────────────────────
        invitation = WorkspaceInvitation.objects.create(
            workspace=workspace,
            email=email,
            role=role,
            invited_by_id=actor_id,
            invited_by_name=actor_name,
        )

        logger.info(
            "workspace.invitation.created",
            extra={
                "invitation_id": str(invitation.id),
                "workspace_id": str(workspace.id),
                "email": email,
                "role": role,
                "actor_id": str(actor_id),
            },
        )

        # ── Publish Kafka event ───────────────────────────────────────────────
        # Event is published inside the transaction — if the transaction rolls
        # back, the event is also not published (producer.flush not called yet).
        # This is intentional: we use transaction.on_commit for Kafka in production.
        # For simplicity here, we publish after the transaction commits below.
        # See: https://docs.djangoproject.com/en/4.2/topics/db/transactions/#performing-actions-after-commit
        transaction.on_commit(
            lambda: self._events.member_invited(
                workspace=workspace,
                invitation=invitation,
                actor_id=actor_id,
            )
        )

        # ── Dispatch email task (after commit) ────────────────────────────────
        transaction.on_commit(
            lambda: _dispatch_invitation_email(str(invitation.id))
        )

        return invitation

    @transaction.atomic
    def accept_invitation(
        self,
        *,
        token: str,
        user_id: uuid.UUID,
        user_email: str,
    ) -> tuple[WorkspaceInvitation, WorkspaceMember]:
        """
        Accept a pending invitation and create a workspace membership.

        Returns (invitation, member) tuple.

        Business rules:
          - Token must exist and not be soft-deleted
          - Invitation must not be expired
          - Invitation must not be already accepted (replay attack prevention)
          - User cannot already be an active member of the workspace
          - select_for_update() prevents concurrent acceptance races

        The lock scope (SELECT FOR UPDATE on the invitation row) prevents two
        concurrent requests with the same token from both succeeding.
        """
        # ── Fetch with row lock ───────────────────────────────────────────────
        try:
            invitation = (
                WorkspaceInvitation.objects
                .select_related("workspace")
                .select_for_update(nowait=False)  # block until lock acquired
                .get(token=token, deleted_at__isnull=True)
            )
        except WorkspaceInvitation.DoesNotExist as exc:
            raise InvitationError("This invitation link is invalid or has been revoked.") from exc

        workspace = invitation.workspace

        if workspace.is_deleted:
            raise InvitationError("This workspace no longer exists.")

        # ── State validation ──────────────────────────────────────────────────
        if invitation.is_accepted:
            raise InvitationError("This invitation has already been accepted.")

        if invitation.is_expired:
            raise InvitationError(
                "This invitation has expired. Ask an admin to send a new one."
            )
        
        if invitation.email.lower() != user_email.lower():
            raise InvitationError(
                "This invitation was sent to a different email address."
            )

        # ── Duplicate member guard ────────────────────────────────────────────
        if workspace.is_member(user_id):
            # User is already a member — idempotent success
            member = workspace.get_member(user_id)
            invitation.accept()  # mark accepted anyway (clean state)
            logger.info(
                "workspace.invitation.accepted.already_member",
                extra={
                    "invitation_id": str(invitation.id),
                    "user_id": str(user_id),
                    "workspace_id": str(workspace.id),
                },
            )
            return invitation, member

        # ── Create membership ─────────────────────────────────────────────────
        # Handles the case where a user was previously removed (soft-deleted member)
        existing_member = WorkspaceMember.all_objects.filter(
            workspace=workspace,
            user_id=user_id,
        ).first()

        if existing_member and existing_member.is_deleted:
            # Restore with new role from invitation
            existing_member.role = invitation.role
            existing_member.deleted_at = None
            existing_member.joined_at = timezone.now()
            existing_member.invited_by_id = invitation.invited_by_id
            existing_member.save(
                update_fields=["role", "deleted_at", "joined_at", "invited_by_id", "updated_at"]
            )
            member = existing_member
        else:
            member = WorkspaceMember.objects.create(
                workspace=workspace,
                user_id=user_id,
                role=invitation.role,
                joined_at=timezone.now(),
                invited_by_id=invitation.invited_by_id,
            )

        # ── Mark invitation accepted ──────────────────────────────────────────
        invitation.accept()

        logger.info(
            "workspace.invitation.accepted",
            extra={
                "invitation_id": str(invitation.id),
                "user_id": str(user_id),
                "workspace_id": str(workspace.id),
                "role": member.role,
            },
        )

        # ── Post-commit side effects ──────────────────────────────────────────
        transaction.on_commit(
            lambda: self._events.member_joined(
                workspace=workspace,
                member=member,
                actor_id=user_id,
            )
        )
        transaction.on_commit(
            lambda: _dispatch_member_joined_notification(
                workspace_id=str(workspace.id),
                user_id=str(user_id),
                role=member.role,
            )
        )

        return invitation, member

    def revoke_invitation(
        self,
        *,
        invitation: WorkspaceInvitation,
        actor_id: uuid.UUID,
    ) -> None:
        """
        Revoke (soft-delete) a pending invitation.
        Admin or owner only. Cannot revoke an already-accepted invitation.
        """
        workspace = invitation.workspace

        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise WorkspacePermissionError(
                "Only workspace admins and owners can revoke invitations."
            )

        if invitation.is_accepted:
            raise InvitationError("Cannot revoke an invitation that has already been accepted.")

        invitation.delete()  # soft delete

        logger.info(
            "workspace.invitation.revoked",
            extra={
                "invitation_id": str(invitation.id),
                "workspace_id": str(workspace.id),
                "actor_id": str(actor_id),
            },
        )

    def list_pending_invitations(self, *, workspace: Workspace) -> "QuerySet[WorkspaceInvitation]":
        """Return pending (non-expired, non-accepted, non-revoked) invitations."""
        return (
            WorkspaceInvitation.objects
            .filter(
                workspace=workspace,
                accepted_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .select_related("workspace")
            .order_by("-created_at")
        )


# ─── Task dispatch helpers (deferred to avoid circular imports) ────────────────

def _dispatch_invitation_email(invitation_id: str) -> None:
    """Fire-and-forget invitation email task."""
    try:
        from .tasks import send_workspace_invitation_email
        send_workspace_invitation_email.delay(invitation_id)
    except Exception as exc:
        logger.error(
            "task.dispatch.invitation_email.failed",
            extra={"invitation_id": invitation_id, "error": str(exc)},
        )


def _dispatch_member_joined_notification(workspace_id: str, user_id: str, role: str) -> None:
    """Fire-and-forget member-joined notification task."""
    try:
        from .tasks import notify_member_joined
        notify_member_joined.delay(workspace_id=workspace_id, user_id=user_id, role=role)
    except Exception as exc:
        logger.error(
            "task.dispatch.member_joined.failed",
            extra={"workspace_id": workspace_id, "user_id": user_id, "error": str(exc)},
        )


def _dispatch_member_removed_notification(
    workspace_id: str,
    removed_user_id: str,
    actor_id: str,
    reason: str,
) -> None:
    """Fire-and-forget member-removed notification task."""
    try:
        from .tasks import notify_member_removed
        notify_member_removed.delay(
            workspace_id=workspace_id,
            removed_user_id=removed_user_id,
            actor_id=actor_id,
            reason=reason,
        )
    except Exception as exc:
        logger.error(
            "task.dispatch.member_removed.failed",
            extra={"workspace_id": workspace_id, "removed_user_id": removed_user_id, "error": str(exc)},
        )     