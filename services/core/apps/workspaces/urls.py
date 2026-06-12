"""
URL configuration for the workspaces app.

All routes are under the /workspace/ prefix (set in core/urls.py).
Full paths:

  Workspace CRUD (KRV-019):
    GET    /workspace/workspaces/
    POST   /workspace/workspaces/
    GET    /workspace/workspaces/{id}/
    PATCH  /workspace/workspaces/{id}/
    DELETE /workspace/workspaces/{id}/

  Member management (KRV-020):
    GET    /workspace/workspaces/{id}/members/
    POST   /workspace/workspaces/{id}/members/invite/
    PATCH  /workspace/workspaces/{id}/members/{user_id}/
    DELETE /workspace/workspaces/{id}/members/{user_id}/

  Invitation management (KRV-020):
    GET    /workspace/workspaces/{id}/invitations/
    DELETE /workspace/workspaces/{id}/invitations/{inv_id}/
    POST   /workspace/invitations/{token}/accept/

URL design decisions:
  - Members use user_id (not member row id) for better API ergonomics
  - Invitation accept is NOT nested under workspaces — the user doesn't know
    which workspace they're joining before they accept; only the token matters
  - All workspace-scoped routes use {workspace_pk} as the outer PK name
    to distinguish from {pk} in nested routes (DRF nested router convention)
"""

from django.urls import path

from .views import (
    InvitationAcceptView,
    InvitationRevokeView,
    WorkspaceInvitationListView,
    WorkspaceMemberViewSet,
    WorkspaceViewSet,
)

# ─── Workspace CRUD ────────────────────────────────────────────────────────────

workspace_list = WorkspaceViewSet.as_view({"get": "list", "post": "create"})

workspace_detail = WorkspaceViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

# ─── Member management ─────────────────────────────────────────────────────────

member_list_invite = WorkspaceMemberViewSet.as_view({"get": "list"})

member_invite = WorkspaceMemberViewSet.as_view({"post": "invite"})

member_detail = WorkspaceMemberViewSet.as_view(
    {"patch": "partial_update", "delete": "destroy"}
)

# ─── URL patterns ──────────────────────────────────────────────────────────────

urlpatterns = [
    # Workspace CRUD
    path("workspaces/", workspace_list, name="workspace-list"),
    path("workspaces/<uuid:pk>/", workspace_detail, name="workspace-detail"),
    # Members — list + role update + remove
    path(
        "workspaces/<uuid:workspace_pk>/members/",
        member_list_invite,
        name="workspace-member-list",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/members/invite/",
        member_invite,
        name="workspace-member-invite",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/members/<uuid:pk>/",
        member_detail,
        name="workspace-member-detail",
    ),
    # Invitations — admin list + revoke
    path(
        "workspaces/<uuid:workspace_pk>/invitations/",
        WorkspaceInvitationListView.as_view(),
        name="workspace-invitation-list",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/invitations/<uuid:invitation_id>/",
        InvitationRevokeView.as_view(),
        name="workspace-invitation-revoke",
    ),
    # Invitation accept — NOT nested under workspace (token is the credential)
    path(
        "invitations/<str:token>/accept/",
        InvitationAcceptView.as_view(),
        name="invitation-accept",
    ),
]
