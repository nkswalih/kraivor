"""
Utility helpers for notification dispatch — fan-out, workspace-wide broadcasts, etc.
"""

import logging

logger = logging.getLogger(__name__)


def fanout_to_workspace_members(
    workspace_id: str,
    notification_type: str,
    title: str,
    body: str = "",
    link: str = "",
    metadata: dict | None = None,
    actor_id: str | None = None,
    exclude_user_id: str | None = None,
) -> int:
    """
    Dispatch a notification to every active member of a workspace,
    optionally excluding one user (e.g. the actor who triggered the event).

    Returns the number of members notified.
    """
    from apps.notifications.tasks import dispatch_notification
    from apps.workspaces.models import Workspace

    try:
        workspace = Workspace.objects.prefetch_related("members").get(id=workspace_id)
    except Workspace.DoesNotExist:
        logger.warning(
            "fanout.workspace_not_found", extra={"workspace_id": workspace_id}
        )
        return 0

    members = workspace.members.filter(deleted_at__isnull=True)
    if exclude_user_id:
        members = members.exclude(user_id=exclude_user_id)

    notified = 0
    for member in members:
        try:
            dispatch_notification.delay(
                user_id=str(member.user_id),
                notification_type=notification_type,
                title=title,
                body=body,
                link=link,
                metadata=metadata or {},
                workspace_id=workspace_id,
                actor_id=actor_id,
            )
            notified += 1
        except Exception as exc:
            logger.error(
                "fanout.member_failed",
                extra={
                    "user_id": str(member.user_id),
                    "notification_type": notification_type,
                    "error": str(exc),
                },
            )

    logger.info(
        "fanout.completed",
        extra={
            "workspace_id": workspace_id,
            "notification_type": notification_type,
            "notified": notified,
        },
    )
    return notified
