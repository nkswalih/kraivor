import uuid
from rest_framework import status
from rest_framework.test import APIRequestFactory

from apps.workspaces.models import Workspace
from apps.workspaces.views import (
    MemberDetailView,
    MemberListCreateView,
    WorkspaceDetailView,
    WorkspaceListView,
)


def _build_request(method, path, user_id=None, data=None):
    factory = APIRequestFactory()
    if data is not None:
        request = getattr(factory, method)(path, data, format="json")
    else:
        request = getattr(factory, method)(path)
    if user_id:
        request.user_id = user_id
    return request


class TestWorkspaceViewSetList:
    def test_returns_user_workspaces(self, workspace, owner_member, db):
        request = _build_request(
            "get", "/workspace/workspaces/", user_id=workspace.owner_id
        )
        view = WorkspaceListView.as_view()
        response = view(request)
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("results") or response.data
        assert len(results) == 1
        assert results[0]["slug"] == workspace.slug

    def test_returns_empty_for_non_member(self, workspace, owner_member, db):
        request = _build_request("get", "/workspace/workspaces/", user_id=uuid.uuid4())
        view = WorkspaceListView.as_view()
        response = view(request)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 0

    def test_returns_401_without_auth(self, db):
        request = _build_request("get", "/workspace/workspaces/")
        view = WorkspaceListView.as_view()
        response = view(request)
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestWorkspaceViewSetCreate:
    def test_creates_workspace(self, db):
        user_id = uuid.uuid4()
        data = {"name": "New Workspace"}
        request = _build_request(
            "post", "/workspace/workspaces/", user_id=user_id, data=data
        )
        view = WorkspaceListView.as_view()
        response = view(request)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Workspace"
        assert response.data["slug"] == "new-workspace"
        assert response.data["owner_id"] == str(user_id)
        assert Workspace.objects.filter(slug="new-workspace").exists()

    def test_returns_400_for_invalid_data(self, db):
        user_id = uuid.uuid4()
        data = {"name": "X"}
        request = _build_request(
            "post", "/workspace/workspaces/", user_id=user_id, data=data
        )
        view = WorkspaceListView.as_view()
        response = view(request)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWorkspaceViewSetRetrieve:
    def test_returns_workspace(self, workspace, owner_member, db):
        request = _build_request(
            "get", f"/workspace/workspaces/{workspace.id}/", user_id=workspace.owner_id
        )
        view = WorkspaceDetailView.as_view()
        response = view(request, pk=str(workspace.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["slug"] == workspace.slug
        assert response.data["owner_id"] == str(workspace.owner_id)

    def test_returns_404_for_non_member(self, workspace, owner_member, db):
        request = _build_request(
            "get", f"/workspace/workspaces/{workspace.id}/", user_id=uuid.uuid4()
        )
        view = WorkspaceDetailView.as_view()
        response = view(request, pk=str(workspace.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_for_invalid_uuid(self, workspace, owner_member, db):
        request = _build_request(
            "get", "/workspace/workspaces/invalid/", user_id=workspace.owner_id
        )
        view = WorkspaceDetailView.as_view()
        response = view(request, pk="not-a-uuid")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWorkspaceViewSetUpdate:
    def test_admin_can_update(self, workspace, admin_member, db):
        data = {"name": "Updated Name"}
        request = _build_request(
            "patch",
            f"/workspace/workspaces/{workspace.id}/",
            user_id=admin_member.user_id,
            data=data,
        )
        view = WorkspaceDetailView.as_view()
        response = view(request, pk=str(workspace.id))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Name"

    def test_member_cannot_update(self, workspace, regular_member, db):
        data = {"name": "Hacked"}
        request = _build_request(
            "patch",
            f"/workspace/workspaces/{workspace.id}/",
            user_id=regular_member.user_id,
            data=data,
        )
        view = WorkspaceDetailView.as_view()
        response = view(request, pk=str(workspace.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_non_member(self, workspace, owner_member, db):
        data = {"name": "Hacked"}
        request = _build_request(
            "patch",
            f"/workspace/workspaces/{workspace.id}/",
            user_id=uuid.uuid4(),
            data=data,
        )
        view = WorkspaceDetailView.as_view()
        response = view(request, pk=str(workspace.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWorkspaceViewSetDelete:
    def test_owner_can_delete(self, workspace, owner_member, db):
        request = _build_request(
            "delete",
            f"/workspace/workspaces/{workspace.id}/",
            user_id=workspace.owner_id,
        )
        view = WorkspaceDetailView.as_view()
        response = view(request, pk=str(workspace.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        workspace.refresh_from_db()
        assert workspace.is_deleted

    def test_admin_cannot_delete(self, workspace, admin_member, db):
        request = _build_request(
            "delete",
            f"/workspace/workspaces/{workspace.id}/",
            user_id=admin_member.user_id,
        )
        view = WorkspaceDetailView.as_view()
        response = view(request, pk=str(workspace.id))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_non_member(self, workspace, owner_member, db):
        request = _build_request(
            "delete", f"/workspace/workspaces/{workspace.id}/", user_id=uuid.uuid4()
        )
        view = WorkspaceDetailView.as_view()
        response = view(request, pk=str(workspace.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWorkspaceMemberViewSetList:
    def test_lists_members(self, workspace, owner_member, admin_member, db):
        request = _build_request(
            "get",
            f"/workspace/workspaces/{workspace.id}/members/",
            user_id=workspace.owner_id,
        )
        view = MemberListCreateView.as_view()
        response = view(request, workspace_pk=str(workspace.id))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_returns_404_for_non_member(self, workspace, owner_member, db):
        request = _build_request(
            "get",
            f"/workspace/workspaces/{workspace.id}/members/",
            user_id=uuid.uuid4(),
        )
        view = MemberListCreateView.as_view()
        response = view(request, workspace_pk=str(workspace.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWorkspaceMemberViewSetCreate:
    def test_admin_can_add_member(self, workspace, admin_member, db):
        view = MemberListCreateView.as_view()

        # Payload requires an email address under KRV-020 contract
        data = {"email": "new_invitee@example.com", "role": "member"}
        request = _build_request(
            "post",
            f"/workspace/workspaces/{workspace.id}/members/invite/",
            user_id=admin_member.user_id,
            data=data,
        )

        response = view(request, workspace_pk=str(workspace.id))
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "new_invitee@example.com"
        assert response.data["role"] == "member"
        assert "token" in response.data

    def test_returns_400_without_user_id(self, workspace, admin_member, db):
        view = MemberListCreateView.as_view()

        data = {"role": "member"}  # Missing "email"
        request = _build_request(
            "post",
            f"/workspace/workspaces/{workspace.id}/members/invite/",
            user_id=admin_member.user_id,
            data=data,
        )

        response = view(request, workspace_pk=str(workspace.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data["detail"]

    def test_returns_400_for_invalid_role(self, workspace, admin_member, db):
        view = MemberListCreateView.as_view()

        data = {"email": "test@example.com", "role": "superadmin"}
        request = _build_request(
            "post",
            f"/workspace/workspaces/{workspace.id}/members/invite/",
            user_id=admin_member.user_id,
            data=data,
        )

        response = view(request, workspace_pk=str(workspace.id))
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "role" in response.data["detail"]


class TestWorkspaceMemberViewSetUpdate:
    def test_admin_can_update_role(self, workspace, admin_member, regular_member, db):
        data = {"role": "viewer"}
        request = _build_request(
            "patch",
            f"/workspace/workspaces/{workspace.id}/members/{regular_member.user_id}/",
            user_id=admin_member.user_id,
            data=data,
        )
        view = MemberDetailView.as_view()
        response = view(
            request, workspace_pk=str(workspace.id), pk=str(regular_member.user_id)
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["role"] == "viewer"

    def test_returns_404_for_invalid_user_id(self, workspace, admin_member, db):
        data = {"role": "viewer"}
        request = _build_request(
            "patch",
            f"/workspace/workspaces/{workspace.id}/members/invalid/",
            user_id=admin_member.user_id,
            data=data,
        )
        view = MemberDetailView.as_view()
        response = view(request, workspace_pk=str(workspace.id), pk="not-a-uuid")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWorkspaceMemberViewSetDelete:
    def test_admin_can_remove_member(self, workspace, admin_member, regular_member, db):
        request = _build_request(
            "delete",
            f"/workspace/workspaces/{workspace.id}/members/{regular_member.user_id}/",
            user_id=admin_member.user_id,
        )
        view = MemberDetailView.as_view()
        response = view(
            request, workspace_pk=str(workspace.id), pk=str(regular_member.user_id)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_member_can_leave(self, workspace, regular_member, db):
        request = _build_request(
            "delete",
            f"/workspace/workspaces/{workspace.id}/members/{regular_member.user_id}/",
            user_id=regular_member.user_id,
        )
        view = MemberDetailView.as_view()
        response = view(
            request, workspace_pk=str(workspace.id), pk=str(regular_member.user_id)
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_returns_404_for_non_member(self, workspace, admin_member, db):
        request = _build_request(
            "delete",
            f"/workspace/workspaces/{workspace.id}/members/{uuid.uuid4()}/",
            user_id=admin_member.user_id,
        )
        view = MemberDetailView.as_view()
        response = view(request, workspace_pk=str(workspace.id), pk=str(uuid.uuid4()))
        assert response.status_code == status.HTTP_404_NOT_FOUND
