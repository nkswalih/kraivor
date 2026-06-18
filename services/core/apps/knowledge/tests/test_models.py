"""
Knowledge Space model tests — KRV-022.

Covers:
  - Field defaults and creation
  - Soft delete lifecycle (is_deleted, delete(), hard_delete())
  - SoftDeleteManager queryset filtering (objects vs all_objects)
  - __str__ representation
"""

import uuid

import pytest

from apps.knowledge.models import KnowledgeSpace


@pytest.mark.django_db
class TestKnowledgeSpaceModel:
    # ── Creation and defaults ─────────────────────────────────────────────────

    def test_creates_with_uuid_pk(self, knowledge_space):
        assert isinstance(knowledge_space.id, uuid.UUID)

    def test_canvas_data_defaults_to_empty_dict(self, workspace, owner_id):
        ks = KnowledgeSpace.objects.create(
            workspace=workspace, name="Minimal Space", created_by=owner_id
        )
        assert ks.canvas_data == {}

    def test_description_defaults_to_null(self, workspace, owner_id):
        ks = KnowledgeSpace.objects.create(
            workspace=workspace, name="No Description", created_by=owner_id
        )
        assert ks.description is None

    def test_updated_by_defaults_to_null(self, knowledge_space):
        assert knowledge_space.updated_by is None

    def test_created_by_stored_correctly(self, knowledge_space, owner_id):
        assert knowledge_space.created_by == owner_id

    def test_created_at_set_on_creation(self, knowledge_space):
        assert knowledge_space.created_at is not None

    def test_updated_at_set_on_creation(self, knowledge_space):
        assert knowledge_space.updated_at is not None

    def test_deleted_at_is_null_for_new_space(self, knowledge_space):
        assert knowledge_space.deleted_at is None

    # ── __str__ ───────────────────────────────────────────────────────────────

    def test_str_representation(self, knowledge_space, workspace):
        expected = f"KnowledgeSpace('Authentication System'@{workspace.slug})"
        assert str(knowledge_space) == expected

    # ── Soft delete lifecycle ─────────────────────────────────────────────────

    def test_is_deleted_false_for_active_space(self, knowledge_space):
        assert knowledge_space.is_deleted is False

    def test_delete_sets_deleted_at_on_instance(self, knowledge_space):
        """
        TimestampedModel.delete() sets deleted_at on the in-memory Python
        instance — tests can check is_deleted without re-fetching from DB.
        """
        knowledge_space.delete()
        assert knowledge_space.deleted_at is not None
        assert knowledge_space.is_deleted is True

    def test_soft_deleted_space_excluded_from_default_manager(self, knowledge_space):
        ks_id = knowledge_space.id
        knowledge_space.delete()
        assert not KnowledgeSpace.objects.filter(id=ks_id).exists()

    def test_soft_deleted_space_visible_via_all_objects(self, knowledge_space):
        ks_id = knowledge_space.id
        knowledge_space.delete()
        assert KnowledgeSpace.all_objects.filter(id=ks_id).exists()

    def test_hard_delete_removes_row_permanently(self, knowledge_space):
        ks_id = knowledge_space.id
        knowledge_space.hard_delete()
        assert not KnowledgeSpace.all_objects.filter(id=ks_id).exists()

    # ── SoftDeleteManager queryset ────────────────────────────────────────────

    def test_objects_returns_only_active_spaces(
        self, workspace, owner_id, knowledge_space
    ):
        active = KnowledgeSpace.objects.create(
            workspace=workspace, name="Active Space", created_by=owner_id
        )
        knowledge_space.delete()

        live = list(KnowledgeSpace.objects.filter(workspace=workspace))
        assert len(live) == 1
        assert live[0].id == active.id

    def test_all_objects_returns_active_and_deleted(
        self, workspace, owner_id, knowledge_space
    ):
        KnowledgeSpace.objects.create(
            workspace=workspace, name="Active Space", created_by=owner_id
        )
        knowledge_space.delete()

        all_ks = KnowledgeSpace.all_objects.filter(workspace=workspace)
        assert all_ks.count() == 2

    # ── canvas_data field ─────────────────────────────────────────────────────

    def test_canvas_data_stores_complex_json(self, workspace, owner_id):
        payload = {
            "nodes": [
                {"id": "n1", "type": "text", "x": 100, "y": 200, "data": "hello"}
            ],
            "edges": [{"from": "n1", "to": "n2"}],
            "viewport": {"x": 0, "y": 0, "zoom": 1.0},
        }
        ks = KnowledgeSpace.objects.create(
            workspace=workspace,
            name="Complex Canvas",
            canvas_data=payload,
            created_by=owner_id,
        )
        ks.refresh_from_db()
        assert ks.canvas_data["nodes"][0]["type"] == "text"
        assert ks.canvas_data["viewport"]["zoom"] == 1.0

    def test_canvas_data_updated_by_save(self, knowledge_space):
        new_data = {"nodes": [{"id": "sticky-1", "type": "sticky_note"}]}
        knowledge_space.canvas_data = new_data
        knowledge_space.save(update_fields=["canvas_data", "updated_at"])

        # Fetch fresh from DB (not soft-deleted, so .objects is fine)
        refreshed = KnowledgeSpace.objects.get(id=knowledge_space.id)
        assert refreshed.canvas_data == new_data
