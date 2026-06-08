import uuid

from django.test import RequestFactory

from apps.workspaces.permissions import (
    IsAuthenticated,
    IsWorkspaceAdmin,
    IsWorkspaceMember,
    IsWorkspaceOwner,
)


class TestIsAuthenticated:
    def test_has_permission_returns_true_with_user_id(self):
        request = RequestFactory().get("/")
        request.user_id = uuid.uuid4()
        assert IsAuthenticated().has_permission(request, None)

    def test_has_permission_returns_false_without_user_id(self):
        request = RequestFactory().get("/")
        assert not IsAuthenticated().has_permission(request, None)

    def test_has_permission_returns_false_with_none_user_id(self):
        request = RequestFactory().get("/")
        request.user_id = None
        assert not IsAuthenticated().has_permission(request, None)


class TestIsWorkspaceMember:
    def test_has_permission_returns_true_with_user_id(self):
        request = RequestFactory().get("/")
        request.user_id = uuid.uuid4()
        assert IsWorkspaceMember().has_permission(request, None)

    def test_has_permission_returns_false_without_user_id(self):
        request = RequestFactory().get("/")
        assert not IsWorkspaceMember().has_permission(request, None)

    def test_has_object_permission_returns_true_for_member(self, workspace, owner_member, db):
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id
        perm = IsWorkspaceMember()
        assert perm.has_object_permission(request, None, workspace)

    def test_has_object_permission_returns_false_for_non_member(self, workspace, db):
        request = RequestFactory().get("/")
        request.user_id = uuid.uuid4()
        perm = IsWorkspaceMember()
        assert not perm.has_object_permission(request, None, workspace)

    def test_has_object_permission_returns_false_without_user_id(self, workspace, db):
        request = RequestFactory().get("/")
        perm = IsWorkspaceMember()
        assert not perm.has_object_permission(request, None, workspace)

    def test_has_object_permission_accepts_workspace_member_object(
        self, workspace, owner_member, db
    ):
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id
        perm = IsWorkspaceMember()
        assert perm.has_object_permission(request, None, owner_member)

    def test_has_object_permission_fails_deleted_member(self, workspace, owner_member, db):
        owner_member.delete()
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id
        perm = IsWorkspaceMember()
        assert not perm.has_object_permission(request, None, workspace)


class TestIsWorkspaceAdmin:
    def test_has_permission_returns_true_with_user_id(self):
        request = RequestFactory().get("/")
        request.user_id = uuid.uuid4()
        assert IsWorkspaceAdmin().has_permission(request, None)

    def test_has_permission_returns_false_without_user_id(self):
        request = RequestFactory().get("/")
        assert not IsWorkspaceAdmin().has_permission(request, None)

    def test_has_object_permission_returns_true_for_admin(self, workspace, admin_member, db):
        request = RequestFactory().get("/")
        request.user_id = admin_member.user_id
        perm = IsWorkspaceAdmin()
        assert perm.has_object_permission(request, None, workspace)

    def test_has_object_permission_returns_true_for_owner(self, workspace, owner_member, db):
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id
        perm = IsWorkspaceAdmin()
        assert perm.has_object_permission(request, None, workspace)

    def test_has_object_permission_returns_false_for_member(self, workspace, regular_member, db):
        request = RequestFactory().get("/")
        request.user_id = regular_member.user_id
        perm = IsWorkspaceAdmin()
        assert not perm.has_object_permission(request, None, workspace)

    def test_has_object_permission_returns_false_for_non_member(self, workspace, db):
        request = RequestFactory().get("/")
        request.user_id = uuid.uuid4()
        perm = IsWorkspaceAdmin()
        assert not perm.has_object_permission(request, None, workspace)

    def test_has_object_permission_accepts_workspace_member_object(
        self, workspace, admin_member, db
    ):
        request = RequestFactory().get("/")
        request.user_id = admin_member.user_id
        perm = IsWorkspaceAdmin()
        assert perm.has_object_permission(request, None, admin_member)


class TestIsWorkspaceOwner:
    def test_has_permission_returns_true_with_user_id(self):
        request = RequestFactory().get("/")
        request.user_id = uuid.uuid4()
        assert IsWorkspaceOwner().has_permission(request, None)

    def test_has_permission_returns_false_without_user_id(self):
        request = RequestFactory().get("/")
        assert not IsWorkspaceOwner().has_permission(request, None)

    def test_has_object_permission_returns_true_for_owner(self, workspace, owner_member, db):
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id
        perm = IsWorkspaceOwner()
        assert perm.has_object_permission(request, None, workspace)

    def test_has_object_permission_returns_false_for_admin(self, workspace, admin_member, db):
        request = RequestFactory().get("/")
        request.user_id = admin_member.user_id
        perm = IsWorkspaceOwner()
        assert not perm.has_object_permission(request, None, workspace)

    def test_has_object_permission_returns_false_for_member(self, workspace, regular_member, db):
        request = RequestFactory().get("/")
        request.user_id = regular_member.user_id
        perm = IsWorkspaceOwner()
        assert not perm.has_object_permission(request, None, workspace)

    def test_has_object_permission_returns_true_for_owner_with_member_object(
        self, workspace, owner_member, db
    ):
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id
        perm = IsWorkspaceOwner()
        assert perm.has_object_permission(request, None, owner_member)
