from django.urls import path

from .views import (
    InvitationAcceptView,
    InvitationListAdminView,
    InvitationRevokeView,
    MemberDetailView,
    MemberListCreateView,
    WorkspaceDetailView,
    WorkspaceListView,
)

urlpatterns = [
    path("workspaces/", WorkspaceListView.as_view(), name="workspace-list"),
    path(
        "workspaces/<uuid:pk>/", WorkspaceDetailView.as_view(), name="workspace-detail"
    ),
    path(
        "workspaces/<uuid:workspace_pk>/members/",
        MemberListCreateView.as_view(),
        name="workspace-member-list",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/members/invite/",
        MemberListCreateView.as_view(),
        name="workspace-member-invite",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/members/<uuid:pk>/",
        MemberDetailView.as_view(),
        name="workspace-member-detail",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/invitations/",
        InvitationListAdminView.as_view(),
        name="workspace-invitation-list",
    ),
    path(
        "workspaces/<uuid:workspace_pk>/invitations/<uuid:invitation_id>/",
        InvitationRevokeView.as_view(),
        name="workspace-invitation-revoke",
    ),
    path(
        "invitations/<str:token>/accept/",
        InvitationAcceptView.as_view(),
        name="invitation-accept",
    ),
]
