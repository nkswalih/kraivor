"""DRF permission classes for workspace and project-level authorization.

- ``IsWorkspaceMember`` — request-level permission checking workspace membership via
  ``request.workspace_id`` header.
- ``IsProjectOwnerOrWorkspaceAdmin`` — object-level permission allowing the project
  owner or a workspace owner/admin to mutate the resource.

ADR: The project views use ``_get_workspace_or_404`` (404 for non-members) instead
of ``IsWorkspaceMember`` (403 for non-members) to avoid leaking workspace existence.
These permission classes remain available for other call sites that need explicit 403.
"""

import logging
from rest_framework.permissions import BasePermission

from apps.workspaces.models import WorkspaceMember

logger = logging.getLogger(__name__)


class IsWorkspaceMember(BasePermission):
    message = "You must be an active member of this workspace."

    def has_permission(self, request, view) -> bool:
        workspace_id = getattr(request, "workspace_id", None)
        user_id = getattr(request, "user_id", None)

        if not workspace_id or not user_id:
            return False

        return WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user_id=user_id,
        ).exists()


class IsProjectOwnerOrWorkspaceAdmin(BasePermission):
    message = "Only the project owner or workspace admins can perform this action."

    def has_object_permission(self, request, view, obj) -> bool:
        user_id = str(request.user_id)

        if str(obj.owner_id) == user_id:
            return True

        return WorkspaceMember.objects.filter(
            workspace_id=obj.workspace_id,
            user_id=user_id,
            role__in=["owner", "admin"],
        ).exists()
