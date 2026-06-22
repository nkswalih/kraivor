from typing import TYPE_CHECKING

import uuid
from rest_framework.exceptions import NotFound

if TYPE_CHECKING:
    from apps.workspaces.models import Workspace

from ..selectors import WorkspaceSelector
from .invitations import (
    InvitationAcceptView,
    InvitationListAdminView,
    InvitationRevokeView,
)
from .members import MemberDetailView, MemberListCreateView
from .workspaces import WorkspaceDetailView, WorkspaceListView


class WorkspaceContextMixin:
    def _get_user_id(self) -> uuid.UUID:
        return self.request.user_id

    def _get_actor_name(self) -> str:
        return getattr(self.request, "user_name", "") or "A team member"

    def _get_workspace_or_404(self, pk: str) -> "Workspace":
        try:
            workspace_id = pk if isinstance(pk, uuid.UUID) else uuid.UUID(str(pk))
        except (ValueError, AttributeError) as exc:
            raise NotFound("Workspace not found.") from exc

        user_id = self._get_user_id()
        workspace = WorkspaceSelector.get_workspace_for_user(workspace_id, user_id)
        if not workspace:
            raise NotFound("Workspace not found.")
        return workspace


__all__ = [
    "WorkspaceListView",
    "WorkspaceDetailView",
    "MemberListCreateView",
    "MemberDetailView",
    "InvitationListAdminView",
    "InvitationRevokeView",
    "InvitationAcceptView",
    "WorkspaceContextMixin",
]
