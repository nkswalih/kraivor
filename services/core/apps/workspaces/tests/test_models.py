import uuid

from django.utils import timezone

from apps.workspaces.constants import WorkspaceRole
from apps.workspaces.models import Workspace, WorkspaceMember


class TestSoftDeleteQuerySet:
    def test_alive_returns_non_deleted(self, workspace, db):
        assert Workspace.objects.filter(id=workspace.id).alive().exists()

    def test_deleted_returns_soft_deleted(self, workspace, db):
        workspace.delete()
        result = Workspace.objects.all_with_deleted().filter(id=workspace.id)
        assert result.deleted().exists()

    def test_delete_soft_deletes(self, workspace, db):
        Workspace.objects.filter(id=workspace.id).delete()
        workspace.refresh_from_db()
        assert workspace.deleted_at is not None

    def test_hard_delete_removes_permanently(self, workspace, db):
        pk = workspace.pk
        Workspace.objects.filter(id=pk).hard_delete()
        assert not Workspace.all_objects.filter(id=pk).exists()


class TestSoftDeleteManager:
    def test_default_queryset_excludes_deleted(self, workspace, db):
        workspace.delete()
        assert Workspace.objects.count() == 0

    def test_all_with_deleted_includes_deleted(self, workspace, db):
        workspace.delete()
        assert Workspace.objects.all_with_deleted().count() == 1


class TestTimestampedModel:
    def test_auto_fields_on_create(self, workspace, db):
        assert workspace.id is not None
        assert workspace.created_at is not None
        assert workspace.updated_at is not None
        assert workspace.deleted_at is None

    def test_soft_delete_sets_deleted_at(self, workspace, db):
        workspace.delete()
        assert workspace.deleted_at is not None
        assert workspace.is_deleted

    def test_hard_delete_removes_instance(self, workspace, db):
        pk = workspace.pk
        workspace.hard_delete()
        assert not Workspace.all_objects.filter(pk=pk).exists()

    def test_objects_excludes_deleted(self, workspace, db):
        workspace.delete()
        assert Workspace.objects.filter(pk=workspace.pk).count() == 0

    def test_all_objects_includes_deleted(self, workspace, db):
        workspace.delete()
        assert Workspace.all_objects.filter(pk=workspace.pk).exists()


class TestWorkspaceModel:
    def test_str_representation(self, workspace, db):
        assert str(workspace) == f"Workspace({workspace.slug})"

    def test_get_member_returns_member(self, workspace, owner_member, db):
        member = workspace.get_member(owner_member.user_id)
        assert member == owner_member

    def test_get_member_returns_none_for_non_member(self, workspace, db):
        assert workspace.get_member(uuid.uuid4()) is None

    def test_get_member_role_returns_role(self, workspace, owner_member, db):
        assert workspace.get_member_role(owner_member.user_id) == WorkspaceRole.OWNER

    def test_get_member_role_returns_none_for_non_member(self, workspace, db):
        assert workspace.get_member_role(uuid.uuid4()) is None

    def test_is_owner_true(self, workspace, owner_member, db):
        assert workspace.is_owner(owner_member.user_id)

    def test_is_owner_false_for_admin(self, workspace, admin_member, db):
        assert not workspace.is_owner(admin_member.user_id)

    def test_is_member_true(self, workspace, owner_member, db):
        assert workspace.is_member(owner_member.user_id)

    def test_is_member_false_for_non_member(self, workspace, db):
        assert not workspace.is_member(uuid.uuid4())

    def test_member_count(
        self, workspace, owner_member, admin_member, regular_member, db
    ):
        assert workspace.member_count == 3

    def test_member_count_excludes_deleted(
        self, workspace, owner_member, admin_member, db
    ):
        admin_member.delete()
        assert workspace.member_count == 1

    def test_default_plan_is_free(self, workspace, db):
        assert workspace.plan == "free"


class TestWorkspaceMemberModel:
    def test_str_representation(self, workspace, owner_member, db):
        expected = (
            f"Member({owner_member.user_id}@{workspace.slug}:{owner_member.role})"
        )
        assert str(owner_member) == expected

    def test_can_admin_true_for_owner(self, owner_member, db):
        assert owner_member.can_admin

    def test_can_admin_true_for_admin(self, admin_member, db):
        assert admin_member.can_admin

    def test_can_admin_false_for_member(self, workspace, db):
        member = WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=uuid.uuid4(),
            role=WorkspaceRole.MEMBER,
            joined_at=timezone.now(),
        )
        assert not member.can_admin

    def test_can_admin_false_for_viewer(self, workspace, db):
        member = WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=uuid.uuid4(),
            role=WorkspaceRole.VIEWER,
            joined_at=timezone.now(),
        )
        assert not member.can_admin

    def test_can_write_true_for_owner(self, owner_member, db):
        assert owner_member.can_write

    def test_can_write_true_for_admin(self, admin_member, db):
        assert admin_member.can_write

    def test_can_write_true_for_member(self, regular_member, db):
        assert regular_member.can_write

    def test_can_write_false_for_viewer(self, workspace, db):
        member = WorkspaceMember.objects.create(
            workspace=workspace,
            user_id=uuid.uuid4(),
            role=WorkspaceRole.VIEWER,
            joined_at=timezone.now(),
        )
        assert not member.can_write

    def test_is_owner_true_for_owner(self, owner_member, db):
        assert owner_member.is_owner

    def test_is_owner_false_for_admin(self, admin_member, db):
        assert not admin_member.is_owner

    def test_soft_delete_sets_deleted_at(self, admin_member, db):
        admin_member.delete()
        assert admin_member.deleted_at is not None
        assert admin_member.is_deleted
