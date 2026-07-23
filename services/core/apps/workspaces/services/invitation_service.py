import logging
import uuid
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from ..constants import PLAN_LIMITS, WorkspaceRole
from ..events import WorkspaceEventPublisher
from ..models import Workspace, WorkspaceInvitation, WorkspaceMember
from .workspace_service import (
    WorkspaceLimitError,
    WorkspacePermissionError,
    WorkspaceServiceError,
)

logger = logging.getLogger(__name__)


class InvitationError(WorkspaceServiceError):
    """Invalid invitation state (expired, already accepted, duplicate)."""


class InvitationService:
    def __init__(self, event_publisher: WorkspaceEventPublisher | None = None) -> None:
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
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise WorkspacePermissionError(
                "Only workspace admins and owners can invite members."
            )
        if role == WorkspaceRole.OWNER:
            raise WorkspacePermissionError(
                "Cannot invite someone as an owner. Transfer ownership after they join."
            )
        existing_pending = (
            WorkspaceInvitation.objects.filter(
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
        transaction.on_commit(
            lambda: self._events.member_invited(
                workspace=workspace, invitation=invitation, actor_id=actor_id
            )
        )
        transaction.on_commit(lambda: _dispatch_invitation_email(str(invitation.id)))
        _ws_name = workspace.name
        _inv_email = invitation.email
        _inv_role = invitation.role
        _inviter_name = invitation.invited_by_name
        transaction.on_commit(
            lambda: _dispatch_invitation_notification(
                workspace_name=_ws_name,
                email=_inv_email,
                role=_inv_role,
                invited_by_name=_inviter_name,
                invitation_token=str(invitation.token),
            )
        )
        return invitation

    @transaction.atomic
    def accept_invitation(
        self, *, token: str, user_id: uuid.UUID, user_email: str
    ) -> tuple[WorkspaceInvitation, WorkspaceMember]:
        try:
            invitation = (
                WorkspaceInvitation.objects.select_related("workspace")
                .select_for_update(nowait=False)
                .get(token=token, deleted_at__isnull=True)
            )
        except WorkspaceInvitation.DoesNotExist as exc:
            raise InvitationError(
                "This invitation link is invalid or has been revoked."
            ) from exc
        workspace = invitation.workspace
        if workspace.is_deleted:
            raise InvitationError("This workspace no longer exists.")
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
        if workspace.is_member(user_id):
            member = workspace.get_member(user_id)
            invitation.accept()
            logger.info(
                "workspace.invitation.accepted.already_member",
                extra={
                    "invitation_id": str(invitation.id),
                    "user_id": str(user_id),
                    "workspace_id": str(workspace.id),
                },
            )
            return invitation, member
        existing_member = WorkspaceMember.all_objects.filter(
            workspace=workspace, user_id=user_id
        ).first()
        if existing_member and existing_member.is_deleted:
            existing_member.role = invitation.role
            existing_member.deleted_at = None
            existing_member.joined_at = timezone.now()
            existing_member.invited_by_id = invitation.invited_by_id
            existing_member.save(
                update_fields=[
                    "role",
                    "deleted_at",
                    "joined_at",
                    "invited_by_id",
                    "updated_at",
                ]
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
        transaction.on_commit(
            lambda: self._events.member_joined(
                workspace=workspace, member=member, actor_id=user_id
            )
        )
        transaction.on_commit(
            lambda: _dispatch_member_joined_notification(
                workspace_id=str(workspace.id), user_id=str(user_id), role=member.role
            )
        )
        return invitation, member

    def revoke_invitation(
        self, *, invitation: WorkspaceInvitation, actor_id: uuid.UUID
    ) -> None:
        workspace = invitation.workspace
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise WorkspacePermissionError(
                "Only workspace admins and owners can revoke invitations."
            )
        if invitation.is_accepted:
            raise InvitationError(
                "Cannot revoke an invitation that has already been accepted."
            )
        invitation.delete()
        logger.info(
            "workspace.invitation.revoked",
            extra={
                "invitation_id": str(invitation.id),
                "workspace_id": str(workspace.id),
                "actor_id": str(actor_id),
            },
        )

    def list_pending_invitations(
        self, *, workspace: Workspace
    ) -> "QuerySet[WorkspaceInvitation]":
        return (
            WorkspaceInvitation.objects.filter(
                workspace=workspace,
                accepted_at__isnull=True,
                expires_at__gt=timezone.now(),
            )
            .select_related("workspace")
            .order_by("-created_at")
        )

    def list_my_pending_invitations(
        self, *, email: str
    ) -> "QuerySet[WorkspaceInvitation]":
        return (
            WorkspaceInvitation.objects.filter(
                email=email, accepted_at__isnull=True, expires_at__gt=timezone.now()
            )
            .select_related("workspace")
            .order_by("-created_at")
        )


def _dispatch_invitation_email(invitation_id: str) -> None:
    try:
        from ..tasks import send_workspace_invitation_email

        send_workspace_invitation_email.delay(invitation_id)
    except Exception as exc:
        logger.error(
            "task.dispatch.invitation_email.failed",
            extra={"invitation_id": invitation_id, "error": str(exc)},
        )


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


def _dispatch_invitation_notification(
    workspace_name: str,
    email: str,
    role: str,
    invited_by_name: str,
    invitation_token: str,
) -> None:
    import requests
    from django.conf import settings

    identity_url = getattr(settings, "IDENTITY_SERVICE_URL", "http://identity:8001")
    endpoint = f"{identity_url}/api/auth/internal/resolve-users/"
    try:
        response = requests.post(
            endpoint,
            json={"emails": [email]},
            headers={settings.INTERNAL_REQUEST_HEADER: settings.INTERNAL_REQUEST_SECRET},
            timeout=5,
        )
    except requests.exceptions.RequestException as exc:
        logger.warning(
            "invitation.notification.resolve_failed",
            extra={"email": email, "error": str(exc)},
        )
        return
    if response.status_code != 200:
        logger.warning(
            "invitation.notification.resolve_error",
            extra={"email": email, "status_code": response.status_code},
        )
        return
    data = response.json()
    users = data.get("users", {})
    user_info = users.get(email)
    if not user_info:
        logger.debug("invitation.notification.user_not_found", extra={"email": email})
        return
    user_id = user_info["id"]
    try:
        from apps.notifications.tasks import dispatch_notification

        dispatch_notification.delay(
            user_id=user_id,
            notification_type="workspace.invitation",
            title=f"{invited_by_name or 'A team member'} invited you to {workspace_name}",
            body=f"Role: {role}",
            link=f"/invitations/{invitation_token}",
        )
        logger.info(
            "invitation.notification.dispatched",
            extra={
                "user_id": user_id,
                "email": email,
                "workspace_name": workspace_name,
            },
        )
    except Exception as exc:
        logger.error(
            "invitation.notification.dispatch_failed",
            extra={"user_id": user_id, "email": email, "error": str(exc)},
        )
