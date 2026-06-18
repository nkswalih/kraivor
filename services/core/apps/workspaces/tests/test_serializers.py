import uuid

import pytest
from django.test import RequestFactory

from apps.workspaces.constants import WorkspaceRole
from apps.workspaces.serializers import (
    MemberRoleUpdateSerializer,
    WorkspaceCreateSerializer,
    WorkspaceDetailSerializer,
    WorkspaceListSerializer,
    WorkspaceMemberSerializer,
    WorkspaceUpdateSerializer,
)


class TestWorkspaceMemberSerializer:
    def test_serializes_correct_fields(self, owner_member, db):
        serializer = WorkspaceMemberSerializer(owner_member)
        assert set(serializer.data.keys()) == {
            "id",
            "user_id",
            "role",
            "status",
            "joined_at",
            "invited_by_id",
            "created_at",
            "updated_at",
        }

    def test_read_only_fields(self, owner_member, db):
        serializer = WorkspaceMemberSerializer(
            owner_member,
            data={"user_id": uuid.uuid4(), "role": WorkspaceRole.ADMIN},
            partial=True,
        )
        serializer.is_valid()
        assert "user_id" not in serializer.validated_data


class TestWorkspaceListSerializer:
    def test_serializes_correct_fields(self, workspace, owner_member, db):
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id

        # ADD THIS LINE: (Patches the raw fixture so the serializer detects the field)
        workspace.active_member_count = 1

        serializer = WorkspaceListSerializer(workspace, context={"request": request})
        assert set(serializer.data.keys()) == {
            "id",
            "name",
            "slug",
            "plan",
            "avatar_url",
            "description",
            "active_member_count",
            "current_user_role",
            "created_at",
            "updated_at",
        }

    def test_current_user_role_returns_role(self, workspace, owner_member, db):
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id
        workspace.active_member_count = 1
        serializer = WorkspaceListSerializer(workspace, context={"request": request})
        assert serializer.data["current_user_role"] == WorkspaceRole.OWNER

    def test_current_user_role_returns_none_without_request(self, workspace, db):
        workspace.active_member_count = 1
        serializer = WorkspaceListSerializer(workspace)
        assert serializer.data["current_user_role"] is None

    def test_current_user_role_returns_none_for_non_member(self, workspace, db):
        request = RequestFactory().get("/")
        request.user_id = uuid.uuid4()
        workspace.active_member_count = 1
        serializer = WorkspaceListSerializer(workspace, context={"request": request})
        assert serializer.data["current_user_role"] is None

    def test_member_count_is_read_only(self, workspace, owner_member, db):
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id

        # FIX: Updated key name to match 'active_member_count'
        data = {"active_member_count": 99}
        serializer = WorkspaceListSerializer(
            workspace, data=data, partial=True, context={"request": request}
        )
        serializer.is_valid()
        assert "active_member_count" not in serializer.validated_data


class TestWorkspaceDetailSerializer:
    def test_serializes_members(self, workspace, owner_member, admin_member, db):
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id
        serializer = WorkspaceDetailSerializer(workspace, context={"request": request})
        assert len(serializer.data["members"]) == 2

    def test_includes_owner_id(self, workspace, owner_member, db):
        request = RequestFactory().get("/")
        request.user_id = workspace.owner_id
        serializer = WorkspaceDetailSerializer(workspace, context={"request": request})
        assert serializer.data["owner_id"] == str(workspace.owner_id)


class TestWorkspaceCreateSerializer:
    def test_valid_data_passes_validation(self, db):
        data = {"name": "My Workspace", "slug": "my-workspace"}
        serializer = WorkspaceCreateSerializer(data=data)
        assert serializer.is_valid()

    def test_slug_auto_generated_from_name(self, db):
        data = {"name": "My Workspace"}
        serializer = WorkspaceCreateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data["slug"] == "my-workspace"

    def test_short_name_gets_prefixed_slug(self, db):
        data = {"name": "AB"}
        serializer = WorkspaceCreateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data["slug"].startswith("ws-")

    def test_name_too_short_raises_error(self, db):
        data = {"name": "X"}
        serializer = WorkspaceCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_name_too_long_raises_error(self, db):
        data = {"name": "A" * 256}
        serializer = WorkspaceCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_name_is_stripped(self, db):
        data = {"name": "  My Workspace  "}
        serializer = WorkspaceCreateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "My Workspace"

    def test_duplicate_slug_raises_error(self, workspace, db):
        data = {"name": "New Workspace", "slug": workspace.slug}
        serializer = WorkspaceCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "slug" in serializer.errors

    def test_invalid_slug_format_raises_error(self, db):
        data = {"name": "Test", "slug": "INVALID SLUG!!!"}
        serializer = WorkspaceCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "slug" in serializer.errors

    def test_slug_with_trailing_hyphen_raises_error(self, db):
        data = {"name": "Test", "slug": "my-slug-"}
        serializer = WorkspaceCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert "slug" in serializer.errors

    def test_settings_whitelist_strips_unknown_keys(self, db):
        data = {
            "name": "Test",
            "settings": {"theme": "dark", "unknown_key": "should be stripped"},
        }
        serializer = WorkspaceCreateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data["settings"] == {"theme": "dark"}

    def test_create_raises_not_implemented(self, db):
        data = {"name": "Test", "slug": "test-slug"}
        serializer = WorkspaceCreateSerializer(data=data)
        serializer.is_valid()
        with pytest.raises(
            NotImplementedError, match="Use WorkspaceService.create_workspace"
        ):
            serializer.save()

    def test_unique_slug_appends_counter(self, workspace, db):
        base = workspace.slug[:96]
        result = WorkspaceCreateSerializer._unique_slug(base)
        assert result == f"{base}-1"


class TestWorkspaceUpdateSerializer:
    def test_name_validation(self, db):
        data = {"name": "  Short  "}
        serializer = WorkspaceUpdateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data["name"] == "Short"

    def test_name_too_short_raises_error(self, db):
        data = {"name": "X"}
        serializer = WorkspaceUpdateSerializer(data=data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors

    def test_settings_merges_with_existing(self, workspace, db):
        workspace.settings = {"theme": "light", "timezone": "UTC"}
        workspace.save()
        data = {"settings": {"theme": "dark"}}
        serializer = WorkspaceUpdateSerializer(workspace, data=data, partial=True)
        assert serializer.is_valid()
        assert serializer.validated_data["settings"] == {
            "theme": "dark",
            "timezone": "UTC",
        }

    def test_settings_unknown_keys_stripped(self, workspace, db):
        data = {"settings": {"invalid_key": "value", "theme": "dark"}}
        serializer = WorkspaceUpdateSerializer(workspace, data=data, partial=True)
        assert serializer.is_valid()
        assert "invalid_key" not in serializer.validated_data["settings"]

    def test_read_only_fields(self, workspace, db):
        data = {"id": uuid.uuid4(), "updated_at": "2025-01-01T00:00:00Z"}
        serializer = WorkspaceUpdateSerializer(workspace, data=data, partial=True)
        assert serializer.is_valid()
        assert "id" not in serializer.validated_data


class TestMemberRoleUpdateSerializer:
    def test_valid_admin_role(self):
        serializer = MemberRoleUpdateSerializer(data={"role": "admin"})
        assert serializer.is_valid()

    def test_valid_member_role(self):
        serializer = MemberRoleUpdateSerializer(data={"role": "member"})
        assert serializer.is_valid()

    def test_valid_viewer_role(self):
        serializer = MemberRoleUpdateSerializer(data={"role": "viewer"})
        assert serializer.is_valid()

    def test_owner_role_not_allowed(self):
        serializer = MemberRoleUpdateSerializer(data={"role": "owner"})
        assert not serializer.is_valid()

    def test_invalid_role_raises_error(self):
        serializer = MemberRoleUpdateSerializer(data={"role": "superadmin"})
        assert not serializer.is_valid()
