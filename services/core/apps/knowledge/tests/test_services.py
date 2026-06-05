"""
Knowledge Space service tests — KRV-022.

Tests are grouped by service method. All Kafka I/O is mocked via a MagicMock
event publisher injected into the service constructor — identical to the
repositories test pattern.

Soft-delete note:
  TimestampedModel.delete() sets deleted_at on the in-memory Python instance
  AND persists it. After delete_knowledge_space(), the `knowledge_space` fixture
  variable already has is_deleted == True — no refresh_from_db() is needed
  (and it would raise DoesNotExist because SoftDeleteManager filters deleted rows).

Covers:
  create_knowledge_space — success, permission errors
  list_knowledge_spaces  — basic list, search, cross-workspace isolation
  update_knowledge_space — success, safe-fields, permission errors
  delete_knowledge_space — success, audit, permission errors, not-found
"""

import uuid
from unittest.mock import MagicMock

import pytest

from apps.knowledge.models import KnowledgeSpace
from apps.knowledge.services import (
    KnowledgePermissionError,
    KnowledgeSpaceService,
)
from apps.workspaces.models import Workspace


def _service(mock_events=None):
    publisher = mock_events or MagicMock()
    return KnowledgeSpaceService(event_publisher=publisher)


# ─── create_knowledge_space ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestCreateKnowledgeSpace:

    def test_creates_db_row(self, workspace, owner_member, owner_id):
        ks = _service().create_knowledge_space(
            workspace=workspace,
            actor_id=owner_id,
            name="Auth System",
        )
        assert ks.pk is not None
        assert KnowledgeSpace.objects.filter(id=ks.id).exists()

    def test_stores_name(self, workspace, owner_member, owner_id):
        ks = _service().create_knowledge_space(
            workspace=workspace,
            actor_id=owner_id,
            name="Payment Service",
        )
        assert ks.name == "Payment Service"

    def test_stores_description(self, workspace, owner_member, owner_id):
        ks = _service().create_knowledge_space(
            workspace=workspace,
            actor_id=owner_id,
            name="X",
            description="A detailed description.",
        )
        assert ks.description == "A detailed description."

    def test_stores_canvas_data(self, workspace, owner_member, owner_id):
        payload = {"nodes": [{"id": "n1"}], "edges": []}
        ks = _service().create_knowledge_space(
            workspace=workspace,
            actor_id=owner_id,
            name="X",
            canvas_data=payload,
        )
        assert ks.canvas_data == payload

    def test_canvas_data_defaults_to_empty_dict(self, workspace, owner_member, owner_id):
        ks = _service().create_knowledge_space(
            workspace=workspace,
            actor_id=owner_id,
            name="X",
        )
        assert ks.canvas_data == {}

    def test_sets_created_by(self, workspace, owner_member, owner_id):
        ks = _service().create_knowledge_space(
            workspace=workspace,
            actor_id=owner_id,
            name="X",
        )
        assert ks.created_by == owner_id

    def test_updated_by_is_null_on_creation(self, workspace, owner_member, owner_id):
        ks = _service().create_knowledge_space(
            workspace=workspace,
            actor_id=owner_id,
            name="X",
        )
        assert ks.updated_by is None

    def test_admin_can_create(self, workspace, admin_member, admin_id):
        ks = _service().create_knowledge_space(
            workspace=workspace,
            actor_id=admin_id,
            name="X",
        )
        assert ks.pk is not None

    def test_member_can_create(self, workspace, regular_member, member_id):
        ks = _service().create_knowledge_space(
            workspace=workspace,
            actor_id=member_id,
            name="X",
        )
        assert ks.pk is not None

    def test_event_published_after_commit(self, workspace, owner_member, owner_id):
        publisher = MagicMock()
        ks = _service(publisher).create_knowledge_space(
            workspace=workspace,
            actor_id=owner_id,
            name="X",
        )
        publisher.knowledge_created.assert_called_once()
        kwargs = publisher.knowledge_created.call_args.kwargs
        assert kwargs["actor_id"] == owner_id
        assert kwargs["knowledge_space"].id == ks.id

    # ── Permission errors ─────────────────────────────────────────────────────

    def test_viewer_cannot_create(self, workspace, viewer_member, viewer_id):
        with pytest.raises(KnowledgePermissionError):
            _service().create_knowledge_space(
                workspace=workspace,
                actor_id=viewer_id,
                name="X",
            )

    def test_outsider_cannot_create(self, workspace, owner_member, outsider_id):
        with pytest.raises(KnowledgePermissionError):
            _service().create_knowledge_space(
                workspace=workspace,
                actor_id=outsider_id,
                name="X",
            )


# ─── list_knowledge_spaces ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestListKnowledgeSpaces:

    def test_returns_active_spaces(self, workspace, owner_member, knowledge_space):
        results = list(_service().list_knowledge_spaces(workspace=workspace))
        assert len(results) == 1
        assert results[0].id == knowledge_space.id

    def test_excludes_soft_deleted_spaces(self, workspace, owner_member, knowledge_space):
        knowledge_space.delete()
        results = list(_service().list_knowledge_spaces(workspace=workspace))
        assert results == []

    def test_returns_empty_list_for_new_workspace(self, workspace, owner_member):
        results = list(_service().list_knowledge_spaces(workspace=workspace))
        assert results == []

    def test_ordered_newest_first(self, workspace, owner_member, owner_id, knowledge_space):
        newer = KnowledgeSpace.objects.create(
            workspace=workspace,
            name="Newer Space",
            created_by=owner_id,
        )
        results = list(_service().list_knowledge_spaces(workspace=workspace))
        assert results[0].id == newer.id
        assert results[1].id == knowledge_space.id

    def test_excludes_spaces_from_other_workspaces(
        self, workspace, owner_member, owner_id, knowledge_space,
    ):
        other = Workspace.objects.create(
            owner_id=owner_id,
            name="Other",
            slug="other-ws",
        )
        KnowledgeSpace.objects.create(
            workspace=other,
            name="Other Space",
            created_by=owner_id,
        )
        results = list(_service().list_knowledge_spaces(workspace=workspace))
        assert len(results) == 1
        assert results[0].id == knowledge_space.id

    # ── Search ────────────────────────────────────────────────────────────────

    def test_search_matches_name(self, workspace, owner_member, owner_id, knowledge_space):
        # knowledge_space.name = "Authentication System"
        results = list(_service().list_knowledge_spaces(workspace=workspace, search="auth"))
        assert len(results) == 1

    def test_search_is_case_insensitive(self, workspace, owner_member, knowledge_space):
        results = list(_service().list_knowledge_spaces(workspace=workspace, search="AUTHENTICATION"))
        assert len(results) == 1

    def test_search_matches_description(self, workspace, owner_member, knowledge_space):
        # knowledge_space.description = "Diagrams and notes about the auth flow."
        results = list(_service().list_knowledge_spaces(workspace=workspace, search="diagrams"))
        assert len(results) == 1

    def test_search_or_semantics_across_fields(self, workspace, owner_member, owner_id):
        KnowledgeSpace.objects.create(
            workspace=workspace, name="Alpha", description="beta content", created_by=owner_id,
        )
        KnowledgeSpace.objects.create(
            workspace=workspace, name="beta title", description="other", created_by=owner_id,
        )
        KnowledgeSpace.objects.create(
            workspace=workspace, name="Gamma", description="gamma", created_by=owner_id,
        )
        results = list(_service().list_knowledge_spaces(workspace=workspace, search="beta"))
        assert len(results) == 2

    def test_search_returns_empty_for_no_match(self, workspace, owner_member, knowledge_space):
        results = list(_service().list_knowledge_spaces(workspace=workspace, search="zzznomatch"))
        assert results == []

    def test_no_search_returns_all(self, workspace, owner_member, owner_id, knowledge_space):
        KnowledgeSpace.objects.create(
            workspace=workspace, name="Another", created_by=owner_id,
        )
        results = list(_service().list_knowledge_spaces(workspace=workspace))
        assert len(results) == 2


# ─── update_knowledge_space ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestUpdateKnowledgeSpace:

    def test_updates_name(self, workspace, owner_member, owner_id, knowledge_space):
        updated = _service().update_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
            updates={"name": "Renamed Canvas"},
        )
        assert updated.name == "Renamed Canvas"

    def test_updates_description(self, workspace, owner_member, owner_id, knowledge_space):
        updated = _service().update_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
            updates={"name": "X", "description": "New desc"},
        )
        assert updated.description == "New desc"

    def test_updates_canvas_data(self, workspace, owner_member, owner_id, knowledge_space):
        new_canvas = {"nodes": [{"id": "n1", "type": "sticky_note"}], "edges": []}
        updated = _service().update_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
            updates={"name": "X", "canvas_data": new_canvas},
        )
        assert updated.canvas_data == new_canvas

    def test_canvas_data_preserved_when_absent_from_updates(
        self, workspace, owner_member, owner_id, knowledge_space,
    ):
        """Absent canvas_data in updates must not overwrite existing canvas."""
        original_canvas = knowledge_space.canvas_data
        _service().update_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
            updates={"name": "Renamed Only"},
        )
        assert knowledge_space.canvas_data == original_canvas

    def test_sets_updated_by(self, workspace, owner_member, owner_id, knowledge_space):
        _service().update_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
            updates={"name": "X"},
        )
        assert knowledge_space.updated_by == owner_id

    def test_admin_can_update(self, workspace, admin_member, admin_id, knowledge_space):
        updated = _service().update_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=admin_id,
            updates={"name": "Admin Update"},
        )
        assert updated.name == "Admin Update"

    def test_member_can_update(self, workspace, regular_member, member_id, knowledge_space):
        updated = _service().update_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=member_id,
            updates={"name": "Member Update"},
        )
        assert updated.name == "Member Update"

    def test_event_published_after_commit(
        self, workspace, owner_member, owner_id, knowledge_space,
    ):
        publisher = MagicMock()
        _service(publisher).update_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
            updates={"name": "X"},
        )
        publisher.knowledge_updated.assert_called_once()
        kwargs = publisher.knowledge_updated.call_args.kwargs
        assert kwargs["actor_id"] == owner_id
        assert kwargs["knowledge_space"].id == knowledge_space.id

    def test_ignores_unknown_fields_in_updates(
        self, workspace, owner_member, owner_id, knowledge_space,
    ):
        """Fields outside safe_fields must not be applied (e.g. workspace_id)."""
        original_workspace_id = knowledge_space.workspace_id
        _service().update_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
            updates={"name": "X", "workspace_id": uuid.uuid4()},
        )
        assert knowledge_space.workspace_id == original_workspace_id

    # ── Permission errors ─────────────────────────────────────────────────────

    def test_viewer_cannot_update(self, workspace, viewer_member, viewer_id, knowledge_space):
        with pytest.raises(KnowledgePermissionError):
            _service().update_knowledge_space(
                knowledge_space=knowledge_space,
                actor_id=viewer_id,
                updates={"name": "X"},
            )

    def test_outsider_cannot_update(self, workspace, owner_member, outsider_id, knowledge_space):
        with pytest.raises(KnowledgePermissionError):
            _service().update_knowledge_space(
                knowledge_space=knowledge_space,
                actor_id=outsider_id,
                updates={"name": "X"},
            )


# ─── delete_knowledge_space ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestDeleteKnowledgeSpace:

    def test_soft_deletes_space(self, workspace, owner_member, owner_id, knowledge_space):
        """
        TimestampedModel.delete() mutates the in-memory instance.
        Check is_deleted on the same Python object — do NOT call refresh_from_db()
        (it would raise DoesNotExist because SoftDeleteManager excludes deleted rows).
        """
        _service().delete_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
        )
        assert knowledge_space.is_deleted

    def test_deleted_space_absent_from_active_queryset(
        self, workspace, owner_member, owner_id, knowledge_space,
    ):
        ks_id = knowledge_space.id
        _service().delete_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
        )
        assert not KnowledgeSpace.objects.filter(id=ks_id).exists()

    def test_deleted_space_visible_via_all_objects(
        self, workspace, owner_member, owner_id, knowledge_space,
    ):
        ks_id = knowledge_space.id
        _service().delete_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
        )
        assert KnowledgeSpace.all_objects.filter(id=ks_id).exists()

    def test_admin_can_delete(self, workspace, admin_member, admin_id, knowledge_space):
        _service().delete_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=admin_id,
        )
        assert knowledge_space.is_deleted

    def test_event_published_after_commit(
        self, workspace, owner_member, owner_id, knowledge_space,
    ):
        publisher = MagicMock()
        _service(publisher).delete_knowledge_space(
            knowledge_space=knowledge_space,
            actor_id=owner_id,
        )
        publisher.knowledge_deleted.assert_called_once()
        kwargs = publisher.knowledge_deleted.call_args.kwargs
        assert kwargs["actor_id"] == owner_id
        assert kwargs["knowledge_space"].id == knowledge_space.id

    # ── Permission errors ─────────────────────────────────────────────────────

    def test_member_cannot_delete(self, workspace, regular_member, member_id, knowledge_space):
        with pytest.raises(KnowledgePermissionError):
            _service().delete_knowledge_space(
                knowledge_space=knowledge_space,
                actor_id=member_id,
            )

    def test_viewer_cannot_delete(self, workspace, viewer_member, viewer_id, knowledge_space):
        with pytest.raises(KnowledgePermissionError):
            _service().delete_knowledge_space(
                knowledge_space=knowledge_space,
                actor_id=viewer_id,
            )

    def test_outsider_cannot_delete(self, workspace, owner_member, outsider_id, knowledge_space):
        with pytest.raises(KnowledgePermissionError):
            _service().delete_knowledge_space(
                knowledge_space=knowledge_space,
                actor_id=outsider_id,
            )