import logging

from rest_framework.permissions import BasePermission

from apps.workspaces.models import WorkspaceMember

logger = logging.getLogger(__name__)


class IsChatRoomMember(BasePermission):
    message = "You are not a member of this chat room's workspace."

    def has_permission(self, request, view):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return False

        workspace_pk = view.kwargs.get("workspace_pk")
        if not workspace_pk:
            return False

        return WorkspaceMember.objects.filter(
            workspace_id=workspace_pk, user_id=user_id, deleted_at__isnull=True
        ).exists()


class CanDeleteMessage(BasePermission):
    message = "You can only delete your own messages."

    def has_permission(self, request, view):
        return bool(getattr(request, "user_id", None))

    def has_object_permission(self, request, view, obj):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return False

        sender_id = (
            obj.get("sender_id")
            if isinstance(obj, dict)
            else getattr(obj, "sender_id", None)
        )
        if sender_id == user_id:
            return True

        workspace_pk = view.kwargs.get("workspace_pk")
        if workspace_pk:
            return WorkspaceMember.objects.filter(
                workspace_id=workspace_pk,
                user_id=user_id,
                role__in=["owner", "admin"],
                deleted_at__isnull=True,
            ).exists()

        return False
