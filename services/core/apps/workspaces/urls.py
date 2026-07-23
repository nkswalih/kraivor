from django.urls import path

from .views import (
    InvitationAcceptView,
    InvitationListAdminView,
    InvitationRevokeView,
    MemberDetailView,
    MemberListCreateView,
    MyPendingInvitationsView,
    WorkspaceDetailView,
    WorkspaceListView,
)

urlpatterns = [
    path("workspaces/", WorkspaceListView.as_view(), name="workspace-list"),
    path(
        "workspaces/<str:pk>/", WorkspaceDetailView.as_view(), name="workspace-detail"
    ),
    path(
        "workspaces/<str:workspace_pk>/members/",
        MemberListCreateView.as_view(),
        name="workspace-member-list",
    ),
    path(
        "workspaces/<str:workspace_pk>/members/invite/",
        MemberListCreateView.as_view(),
        name="workspace-member-invite",
    ),
    path(
        "workspaces/<str:workspace_pk>/members/<uuid:pk>/",
        MemberDetailView.as_view(),
        name="workspace-member-detail",
    ),
    path(
        "workspaces/<str:workspace_pk>/invitations/",
        InvitationListAdminView.as_view(),
        name="workspace-invitation-list",
    ),
    path(
        "workspaces/<str:workspace_pk>/invitations/<uuid:invitation_id>/",
        InvitationRevokeView.as_view(),
        name="workspace-invitation-revoke",
    ),
    path(
        "invitations/pending/",
        MyPendingInvitationsView.as_view(),
        name="my-pending-invitations",
    ),
    path(
        "invitations/<str:token>/accept/",
        InvitationAcceptView.as_view(),
        name="invitation-accept",
    ),
]
