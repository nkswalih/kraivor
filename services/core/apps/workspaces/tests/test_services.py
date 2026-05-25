import uuid

import pytest
from django.utils import timezone

from apps.workspaces.constants import WorkspaceRole
from apps.workspaces.models import WorkspaceMember
from apps.workspaces.services import (
    WorkspaceLimitError,
    WorkspaceNotFoundError,
    WorkspacePermissionError,
    WorkspaceService,
    WorkspaceServiceError,
)


class TestCreateWorkspace:
    def test_creates_workspace_and_owner_member(self, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        owner_id = uuid.uuid4()
        ws = service.create_workspace(
            owner_id=owner_id,
            name="New Workspace",
            slug="new-workspace",
        )
        assert ws.name == "New Workspace"
        assert ws.slug == "new-workspace"
        assert ws.owner_id == owner_id
        assert ws.plan == "free"

        member = WorkspaceMember.objects.get(workspace=ws, user_id=owner_id)
        assert member.role == WorkspaceRole.OWNER
        assert member.joined_at is not None

    def test_publishes_workspace_created_event(self, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        owner_id = uuid.uuid4()
        ws = service.create_workspace(
            owner_id=owner_id,
            name="Event Test",
            slug="event-test",
        )
        mock_event_publisher.workspace_created.assert_called_once_with(
            workspace=ws, actor_id=owner_id,
        )

    def test_creates_with_optional_fields(self, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        owner_id = uuid.uuid4()
        ws = service.create_workspace(
            owner_id=owner_id,
            name="Full Workspace",
            slug="full-workspace",
            avatar_url="https://example.com/avatar.png",
            description="A full workspace",
            settings={"theme": "dark"},
        )
        assert ws.avatar_url == "https://example.com/avatar.png"
        assert ws.description == "A full workspace"
        assert ws.settings == {"theme": "dark"}


class TestUpdateWorkspace:
    def test_updates_safe_fields(self, workspace, owner_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        updated = service.update_workspace(
            workspace=workspace,
            actor_id=workspace.owner_id,
            updates={"name": "Updated Name", "description": "New desc"},
        )
        assert updated.name == "Updated Name"
        assert updated.description == "New desc"

    def test_ignores_unsafe_fields(self, workspace, owner_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        updated = service.update_workspace(
            workspace=workspace,
            actor_id=workspace.owner_id,
            updates={"name": "Safe", "plan": "enterprise", "slug": "hacked"},
        )
        assert updated.name == "Safe"
        assert updated.plan == "free"
        assert updated.slug == workspace.slug

    def test_raises_for_non_admin(self, workspace, regular_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="admin"):
            service.update_workspace(
                workspace=workspace,
                actor_id=regular_member.user_id,
                updates={"name": "Hack"},
            )

    def test_raises_for_non_member(self, workspace, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="admin"):
            service.update_workspace(
                workspace=workspace,
                actor_id=uuid.uuid4(),
                updates={"name": "Hack"},
            )


class TestDeleteWorkspace:
    def test_owner_can_delete(self, workspace, owner_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        service.delete_workspace(workspace=workspace, actor_id=workspace.owner_id)
        workspace.refresh_from_db()
        assert workspace.deleted_at is not None
        assert workspace.is_deleted

    def test_soft_deletes_all_members(self, workspace, owner_member, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        service.delete_workspace(workspace=workspace, actor_id=workspace.owner_id)
        admin_member.refresh_from_db()
        assert admin_member.deleted_at is not None

    def test_raises_for_non_owner(self, workspace, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="owner"):
            service.delete_workspace(workspace=workspace, actor_id=admin_member.user_id)

    def test_publishes_deleted_event(self, workspace, owner_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        service.delete_workspace(workspace=workspace, actor_id=workspace.owner_id)
        mock_event_publisher.workspace_deleted.assert_called_once_with(
            workspace=workspace, actor_id=workspace.owner_id,
        )


class TestAddMember:
    def test_admin_can_add_member(self, workspace, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        new_user_id = uuid.uuid4()
        member = service.add_member(
            workspace=workspace,
            actor_id=admin_member.user_id,
            user_id=new_user_id,
            role=WorkspaceRole.MEMBER,
        )
        assert member.user_id == new_user_id
        assert member.role == WorkspaceRole.MEMBER
        assert member.invited_by_id == admin_member.user_id

    def test_raises_for_non_admin(self, workspace, regular_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="admin"):
            service.add_member(
                workspace=workspace,
                actor_id=regular_member.user_id,
                user_id=uuid.uuid4(),
                role=WorkspaceRole.MEMBER,
            )

    def test_raises_for_owner_role(self, workspace, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="owner"):
            service.add_member(
                workspace=workspace,
                actor_id=admin_member.user_id,
                user_id=uuid.uuid4(),
                role=WorkspaceRole.OWNER,
            )

    def test_raises_for_duplicate_active_member(self, workspace, admin_member, regular_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspaceServiceError, match="already a member"):
            service.add_member(
                workspace=workspace,
                actor_id=admin_member.user_id,
                user_id=regular_member.user_id,
                role=WorkspaceRole.MEMBER,
            )

    def test_restores_soft_deleted_member(self, workspace, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        user_id = uuid.uuid4()
        # Add then delete
        original = WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=user_id,
            role=WorkspaceRole.MEMBER,
        )
        original.delete()
        # Re-add
        member = service.add_member(
            workspace=workspace,
            actor_id=admin_member.user_id,
            user_id=user_id,
            role=WorkspaceRole.ADMIN,
        )
        assert member.id == original.id
        assert member.role == WorkspaceRole.ADMIN
        assert member.deleted_at is None
        assert member.joined_at is not None

    def test_publishes_member_added_event(self, workspace, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        new_user_id = uuid.uuid4()
        service.add_member(
            workspace=workspace,
            actor_id=admin_member.user_id,
            user_id=new_user_id,
            role=WorkspaceRole.MEMBER,
        )
        mock_event_publisher.member_added.assert_called_once()

    def test_enforces_member_limit(self, workspace, owner_member, db, mock_event_publisher):
        # Fill to the FREE plan limit of 3 members
        for _ in range(2):
            WorkspaceMember.objects.create(
                workspace=workspace,
                user_id=uuid.uuid4(),
                role=WorkspaceRole.MEMBER,
                joined_at=timezone.now(),
            )
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspaceLimitError, match="plan allows a maximum"):
            service.add_member(
                workspace=workspace,
                actor_id=workspace.owner_id,
                user_id=uuid.uuid4(),
            )


class TestUpdateMemberRole:
    def test_admin_can_update_member_role(self, workspace, admin_member, regular_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        updated = service.update_member_role(
            workspace=workspace,
            actor_id=admin_member.user_id,
            target_user_id=regular_member.user_id,
            new_role=WorkspaceRole.VIEWER,
        )
        assert updated.role == WorkspaceRole.VIEWER

    def test_raises_for_non_admin(self, workspace, regular_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="admin"):
            service.update_member_role(
                workspace=workspace,
                actor_id=regular_member.user_id,
                target_user_id=uuid.uuid4(),
                new_role=WorkspaceRole.VIEWER,
            )

    def test_raises_for_owner_role_assignment(self, workspace, admin_member, regular_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="owner"):
            service.update_member_role(
                workspace=workspace,
                actor_id=admin_member.user_id,
                target_user_id=regular_member.user_id,
                new_role=WorkspaceRole.OWNER,
            )

    def test_raises_for_non_existent_target(self, workspace, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspaceNotFoundError, match="not a member"):
            service.update_member_role(
                workspace=workspace,
                actor_id=admin_member.user_id,
                target_user_id=uuid.uuid4(),
                new_role=WorkspaceRole.VIEWER,
            )

    def test_raises_when_changing_owner_role(self, workspace, owner_member, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="owner"):
            service.update_member_role(
                workspace=workspace,
                actor_id=admin_member.user_id,
                target_user_id=workspace.owner_id,
                new_role=WorkspaceRole.MEMBER,
            )

    def test_raises_when_admin_changes_another_admin(self, workspace, db, mock_event_publisher):
        admin1 = WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=uuid.uuid4(),
            role=WorkspaceRole.ADMIN,
            joined_at=timezone.now(),
        )
        admin2 = WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=uuid.uuid4(),
            role=WorkspaceRole.ADMIN,
            joined_at=timezone.now(),
        )
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="owner"):
            service.update_member_role(
                workspace=workspace,
                actor_id=admin1.user_id,
                target_user_id=admin2.user_id,
                new_role=WorkspaceRole.MEMBER,
            )

    def test_owner_can_change_admin_role(self, workspace, owner_member, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        updated = service.update_member_role(
            workspace=workspace,
            actor_id=workspace.owner_id,
            target_user_id=admin_member.user_id,
            new_role=WorkspaceRole.MEMBER,
        )
        assert updated.role == WorkspaceRole.MEMBER


class TestRemoveMember:
    def test_member_can_leave(self, workspace, regular_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        service.remove_member(
            workspace=workspace,
            actor_id=regular_member.user_id,
            target_user_id=regular_member.user_id,
        )
        regular_member.refresh_from_db()
        assert regular_member.deleted_at is not None

    def test_admin_can_remove_member(self, workspace, admin_member, regular_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        service.remove_member(
            workspace=workspace,
            actor_id=admin_member.user_id,
            target_user_id=regular_member.user_id,
        )
        regular_member.refresh_from_db()
        assert regular_member.deleted_at is not None

    def test_raises_for_non_existent_member(self, workspace, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspaceNotFoundError, match="not a member"):
            service.remove_member(
                workspace=workspace,
                actor_id=admin_member.user_id,
                target_user_id=uuid.uuid4(),
            )

    def test_raises_when_removing_owner(self, workspace, owner_member, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="owner cannot be removed"):
            service.remove_member(
                workspace=workspace,
                actor_id=admin_member.user_id,
                target_user_id=workspace.owner_id,
            )

    def test_raises_when_admin_removes_another_admin(self, workspace, db, mock_event_publisher):
        admin1 = WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=uuid.uuid4(),
            role=WorkspaceRole.ADMIN,
            joined_at=timezone.now(),
        )
        admin2 = WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=uuid.uuid4(),
            role=WorkspaceRole.ADMIN,
            joined_at=timezone.now(),
        )
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="owner"):
            service.remove_member(
                workspace=workspace,
                actor_id=admin1.user_id,
                target_user_id=admin2.user_id,
            )

    def test_owner_can_remove_admin(self, workspace, owner_member, admin_member, db, mock_event_publisher):
        service = WorkspaceService(event_publisher=mock_event_publisher)
        service.remove_member(
            workspace=workspace,
            actor_id=workspace.owner_id,
            target_user_id=admin_member.user_id,
        )
        admin_member.refresh_from_db()
        assert admin_member.deleted_at is not None

    def test_raises_for_non_admin_removing_others(self, workspace, regular_member, db, mock_event_publisher):
        other = WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=uuid.uuid4(),
            role=WorkspaceRole.VIEWER,
            joined_at=timezone.now(),
        )
        service = WorkspaceService(event_publisher=mock_event_publisher)
        with pytest.raises(WorkspacePermissionError, match="admin"):
            service.remove_member(
                workspace=workspace,
                actor_id=regular_member.user_id,
                target_user_id=other.user_id,
            )
