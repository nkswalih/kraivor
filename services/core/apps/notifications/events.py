import logging

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="workspaces.WorkspaceMember")
def notify_member_joined(sender, instance, created, **kwargs):
    if not created:
        return
    if not instance.workspace_id:
        return
    from apps.notifications.tasks import dispatch_notification

    dispatch_notification.delay(
        user_id=str(instance.user_id),
        notification_type="workspace.member.joined",
        title=f"Welcome to {instance.workspace.name}",
        body=f"You have been added to workspace '{instance.workspace.name}'.",
        workspace_id=str(instance.workspace_id),
        actor_id=str(instance.workspace.owner_id),
    )
    logger.info(
        "signal.member_joined.notification_dispatched",
        extra={"user_id": str(instance.user_id), "workspace_id": str(instance.workspace_id)},
    )


@receiver(pre_delete, sender="workspaces.WorkspaceMember")
def notify_member_removed(sender, instance, **kwargs):
    if not instance.workspace_id:
        return
    from apps.notifications.tasks import dispatch_notification

    dispatch_notification.delay(
        user_id=str(instance.user_id),
        notification_type="workspace.member.removed",
        title=f"Removed from {instance.workspace.name}",
        body=f"You have been removed from workspace '{instance.workspace.name}'.",
        workspace_id=str(instance.workspace_id),
        actor_id=str(instance.workspace.owner_id),
    )
    logger.info(
        "signal.member_removed.notification_dispatched",
        extra={"user_id": str(instance.user_id), "workspace_id": str(instance.workspace_id)},
    )
