"""
Workspace Celery tasks — KRV-020.

All tasks are async-by-default (system design §1):
  "Any operation taking more than 500ms is a background job."

Sending email qualifies — external SMTP/SES call, variable latency.

Task design principles:
  - Tasks are idempotent: safe to retry on failure
  - Tasks receive primitive args (strings, UUIDs as str) — not model instances.
    Model instances are not serializable across Celery's broker boundary.
  - Tasks query the DB themselves to get current state (not rely on stale data
    from when the task was enqueued)
  - Tasks log at INFO level for every significant outcome
  - Tasks use exponential backoff with a ceiling (max_retries=3, countdown grows)

Queue assignment (system design §10):
  invitation tasks → Queue: notifications (2 workers, target latency <30s)
"""

import logging
import uuid

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,         # 30s → 60s → 120s (exponential via retry countdown)
    acks_late=True,                  # ack after task completes, not when received
    reject_on_worker_lost=True,      # re-queue if worker crashes mid-task
    name="workspaces.send_workspace_invitation_email",
)
def send_workspace_invitation_email(
    self,
    invitation_id: str,
) -> dict:
    """
    Send an invitation email to the invitee.

    Args:
        invitation_id: UUID string of the WorkspaceInvitation record.

    Returns:
        dict with outcome metadata for logging/monitoring.

    The task:
      1. Fetches the invitation fresh from DB (not from task args — avoids stale data)
      2. Checks it's still pending (idempotency guard — handles duplicate task dispatch)
      3. Renders the email template
      4. Sends via Django email backend (SES in prod, MailHog in dev)
      5. Updates invitation.email_sent_at
      6. Retries on transient failures with exponential backoff
    """
    from .models import WorkspaceInvitation  # local import to avoid circular

    logger.info(
        "task.invitation_email.started",
        extra={"invitation_id": invitation_id, "task_id": self.request.id},
    )

    try:
        # Fresh DB fetch — task may have been queued seconds/minutes ago
        invitation = (
            WorkspaceInvitation.objects
            .select_related("workspace")
            .get(id=invitation_id)
        )
    except WorkspaceInvitation.DoesNotExist:
        # Invitation deleted between task dispatch and execution — skip silently
        logger.warning(
            "task.invitation_email.not_found",
            extra={"invitation_id": invitation_id},
        )
        return {"status": "skipped", "reason": "invitation_not_found"}

    # Idempotency guard: only send if pending
    if invitation.is_accepted:
        logger.info(
            "task.invitation_email.already_accepted",
            extra={"invitation_id": invitation_id},
        )
        return {"status": "skipped", "reason": "already_accepted"}

    if invitation.is_expired:
        logger.info(
            "task.invitation_email.expired",
            extra={"invitation_id": invitation_id},
        )
        return {"status": "skipped", "reason": "expired"}

    if invitation.email_sent_at:
        # Email was already sent — don't send twice (handles duplicate task dispatch)
        logger.info(
            "task.invitation_email.already_sent",
            extra={"invitation_id": invitation_id, "sent_at": str(invitation.email_sent_at)},
        )
        return {"status": "skipped", "reason": "already_sent"}

    # Build email content
    workspace = invitation.workspace
    context = {
        "workspace_name": workspace.name,
        "inviter_name": invitation.invited_by_name or "A team member",
        "role": invitation.role,
        "accept_url": invitation.accept_url,
        "expires_at": invitation.expires_at,
        "support_email": getattr(settings, "SUPPORT_EMAIL", "support@kraivor.com"),
    }

    subject = f"You've been invited to join {workspace.name} on Kraivor"

    # Render HTML and plain text versions
    try:
        html_body = render_to_string("workspaces/emails/invitation.html", context)
        text_body = render_to_string("workspaces/emails/invitation.txt", context)
    except Exception as exc:
        # Template error — likely a code bug, not transient; don't retry infinitely
        logger.error(
            "task.invitation_email.template_error",
            extra={"invitation_id": invitation_id, "error": str(exc)},
        )
        # Still attempt with fallback plain text
        text_body = _fallback_invitation_text(context)
        html_body = None

    # Send
    try:
        send_mail(
            subject=subject,
            message=text_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@kraivor.com"),
            recipient_list=[invitation.email],
            html_message=html_body,
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(
            "task.invitation_email.send_failed",
            extra={
                "invitation_id": invitation_id,
                "email": invitation.email,
                "error": str(exc),
                "retry_count": self.request.retries,
            },
        )
        # Exponential backoff: 30s, 60s, 120s
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries)) from exc

    # Mark email sent
    invitation.mark_email_sent()

    logger.info(
        "task.invitation_email.sent",
        extra={
            "invitation_id": invitation_id,
            "email": invitation.email,
            "workspace_id": str(workspace.id),
        },
    )

    return {
        "status": "sent",
        "invitation_id": invitation_id,
        "email": invitation.email,
        "workspace_id": str(workspace.id),
    }


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
    name="workspaces.notify_member_joined",
)
def notify_member_joined(
    self,
    workspace_id: str,
    user_id: str,
    role: str,
) -> dict:
    """
    Notify existing workspace members when a new member joins.

    Fanout notification — one task dispatches notifications to all members.
    In high-volume scenarios this should be further broken down per-member,
    but for workspaces (typically <100 members) this is sufficient.

    Args:
        workspace_id: UUID string
        user_id:      UUID string of the new member
        role:         Role the new member received
    """
    from .models import Workspace

    logger.info(
        "task.notify_member_joined.started",
        extra={"workspace_id": workspace_id, "user_id": user_id},
    )

    try:
        workspace = Workspace.objects.prefetch_related("members").get(id=workspace_id)
    except Workspace.DoesNotExist:
        logger.warning(
            "task.notify_member_joined.workspace_not_found",
            extra={"workspace_id": workspace_id},
        )
        return {"status": "skipped", "reason": "workspace_not_found"}

    # Get all admin/owner members to notify (they care about new joins)
    admin_members = workspace.members.filter(
        role__in=["owner", "admin"],
        deleted_at__isnull=True,
    ).exclude(user_id=uuid.UUID(user_id))  # don't notify the joiner about themselves

    notified = 0
    for member in admin_members:
        try:
            # In production: call notification service or dispatch per-user task
            # For now: structured log that notification service consumes
            logger.info(
                "task.notify_member_joined.notify_admin",
                extra={
                    "workspace_id": workspace_id,
                    "new_member_id": user_id,
                    "admin_user_id": str(member.user_id),
                    "role": role,
                },
            )
            notified += 1
        except Exception as exc:
            logger.error(
                "task.notify_member_joined.notify_failed",
                extra={"user_id": str(member.user_id), "error": str(exc)},
            )

    return {"status": "completed", "notified_count": notified}


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=2,
    default_retry_delay=15,
    acks_late=True,
    name="workspaces.notify_member_removed",
)
def notify_member_removed(
    self,
    workspace_id: str,
    removed_user_id: str,
    actor_id: str,
    reason: str = "removed_by_admin",
) -> dict:
    """
    Notify the removed user that they've been removed from the workspace.

    Args:
        workspace_id:     UUID string
        removed_user_id:  UUID string of the removed user
        actor_id:         UUID string of who removed them
        reason:           'removed_by_admin' | 'left'
    """
    from .models import Workspace

    try:
        workspace = Workspace.objects.get(id=workspace_id)
    except Workspace.DoesNotExist:
        return {"status": "skipped", "reason": "workspace_not_found"}

    # In production: call notification service with the removed user's email
    # Email address comes from identity service (separate API call)
    logger.info(
        "task.notify_member_removed.dispatched",
        extra={
            "workspace_id": workspace_id,
            "removed_user_id": removed_user_id,
            "actor_id": actor_id,
            "reason": reason,
            "workspace_name": workspace.name,
        },
    )

    return {"status": "dispatched", "workspace_id": workspace_id}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fallback_invitation_text(context: dict) -> str:
    """Plain-text invitation email when templates fail to render."""
    return (
        f"Hi,\n\n"
        f"{context['inviter_name']} has invited you to join "
        f"'{context['workspace_name']}' on Kraivor as a {context['role']}.\n\n"
        f"Accept your invitation:\n{context['accept_url']}\n\n"
        f"This invitation expires at {context['expires_at']}.\n\n"
        f"If you have questions, contact us at {context['support_email']}.\n\n"
        f"— The Kraivor Team"
    )
