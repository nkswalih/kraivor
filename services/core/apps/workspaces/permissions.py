"""
Workspace permission classes for DRF views.

Authorization model (from system design §11):
  The gateway adds X-User-ID and X-Workspace-ID headers to every request.
  Services trust these headers — they do NOT re-verify the JWT.
  request.user_id is set by the GatewayAuthMiddleware in core's middleware.

Permission check levels:
  1. IsAuthenticated      — X-User-ID header present and valid UUID
  2. IsWorkspaceMember    — user is an active member of the target workspace
  3. IsWorkspaceAdmin     — user has admin or owner role
  4. IsWorkspaceOwner     — user has owner role specifically

These are DRF permission classes — return True/False, raise PermissionDenied on failure.
Business rule enforcement (e.g. plan limits) is in the service layer, not here.
"""

from rest_framework.permissions import BasePermission


class IsAuthenticated(BasePermission):
    """
    Verifies request.user_id was set by GatewayAuthMiddleware.
    This replaces DRF's default IsAuthenticated which expects a Django User object.
    In our architecture, the gateway handles JWT verification — we just trust the header.
    """

    message = "Authentication required."

    def has_permission(self, request, view) -> bool:
        return bool(getattr(request, "user_id", None))


class IsWorkspaceMember(BasePermission):
    """
    Object-level permission: the requesting user is a member of the workspace.
    Applies to all workspace operations — even read requires membership.
    """

    message = "You are not a member of this workspace."

    def has_permission(self, request, view) -> bool:
        return bool(getattr(request, "user_id", None))

    def has_object_permission(self, request, view, obj) -> bool:
        from .models import WorkspaceMember
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return False

        # obj could be Workspace or WorkspaceMember
        if isinstance(obj, WorkspaceMember):
            workspace = obj.workspace
        else:
            workspace = obj

        return workspace.is_member(user_id)


class IsWorkspaceAdmin(BasePermission):
    """
    Object-level: user has admin or owner role in the workspace.
    Used for: update workspace settings, manage members.
    """

    message = "You need admin or owner role to perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(getattr(request, "user_id", None))

    def has_object_permission(self, request, view, obj) -> bool:
        from .models import WorkspaceMember
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return False

        if isinstance(obj, WorkspaceMember):
            workspace = obj.workspace
        else:
            workspace = obj

        member = workspace.get_member(user_id)
        return bool(member and member.can_admin)


class IsWorkspaceOwner(BasePermission):
    """
    Object-level: user is the owner of the workspace.
    Used for: delete workspace, transfer ownership.
    """

    message = "Only the workspace owner can perform this action."

    def has_permission(self, request, view) -> bool:
        return bool(getattr(request, "user_id", None))

    def has_object_permission(self, request, view, obj) -> bool:
        user_id = getattr(request, "user_id", None)
        if not user_id:
            return False

        if hasattr(obj, "workspace"):
            workspace = obj.workspace
        else:
            workspace = obj

        return workspace.is_owner(user_id)