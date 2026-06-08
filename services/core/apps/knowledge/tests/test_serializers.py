"""
Knowledge Space serializer tests — KRV-022.

Covers:
  KnowledgeSpaceCreateSerializer — valid input, all error paths
  KnowledgeSpaceUpdateSerializer — valid input, all error paths
  KnowledgeSpaceListSerializer   — output shape (no canvas_data)
  KnowledgeSpaceSerializer       — output shape (full, with canvas_data)
"""

import uuid

import pytest

from apps.knowledge.serializers import (
    KnowledgeSpaceCreateSerializer,
    KnowledgeSpaceListSerializer,
    KnowledgeSpaceSerializer,
    KnowledgeSpaceUpdateSerializer,
)

# ─── KnowledgeSpaceCreateSerializer ──────────────────────────────────────────


class TestKnowledgeSpaceCreateSerializer:
    def test_valid_minimal_input(self):
        s = KnowledgeSpaceCreateSerializer(data={"name": "Auth Flow"})
        assert s.is_valid(), s.errors

    def test_valid_full_input(self):
        s = KnowledgeSpaceCreateSerializer(
            data={
                "name": "Auth Flow",
                "description": "OAuth and JWT diagrams.",
                "canvas_data": {"nodes": [], "edges": []},
            }
        )
        assert s.is_valid(), s.errors

    def test_name_is_stripped(self):
        s = KnowledgeSpaceCreateSerializer(data={"name": "  Auth Flow  "})
        assert s.is_valid(), s.errors
        assert s.validated_data["name"] == "Auth Flow"

    def test_description_defaults_to_none_when_absent(self):
        s = KnowledgeSpaceCreateSerializer(data={"name": "X"})
        assert s.is_valid(), s.errors
        assert s.validated_data["description"] is None

    def test_canvas_data_defaults_to_empty_dict_when_absent(self):
        s = KnowledgeSpaceCreateSerializer(data={"name": "X"})
        assert s.is_valid(), s.errors
        assert s.validated_data["canvas_data"] == {}

    def test_invalid_missing_name(self):
        s = KnowledgeSpaceCreateSerializer(data={})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_invalid_blank_name(self):
        s = KnowledgeSpaceCreateSerializer(data={"name": "   "})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_invalid_name_too_long(self):
        s = KnowledgeSpaceCreateSerializer(data={"name": "x" * 256})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_invalid_canvas_data_is_list(self):
        s = KnowledgeSpaceCreateSerializer(data={"name": "X", "canvas_data": [1, 2, 3]})
        assert not s.is_valid()
        assert "canvas_data" in s.errors

    def test_invalid_canvas_data_is_scalar(self):
        s = KnowledgeSpaceCreateSerializer(data={"name": "X", "canvas_data": "string"})
        assert not s.is_valid()
        assert "canvas_data" in s.errors

    def test_description_allows_null(self):
        s = KnowledgeSpaceCreateSerializer(data={"name": "X", "description": None})
        assert s.is_valid(), s.errors

    def test_description_allows_blank_string(self):
        s = KnowledgeSpaceCreateSerializer(data={"name": "X", "description": ""})
        assert s.is_valid(), s.errors


# ─── KnowledgeSpaceUpdateSerializer ──────────────────────────────────────────


class TestKnowledgeSpaceUpdateSerializer:
    def test_valid_name_only(self):
        s = KnowledgeSpaceUpdateSerializer(data={"name": "Renamed Canvas"})
        assert s.is_valid(), s.errors

    def test_valid_all_fields(self):
        s = KnowledgeSpaceUpdateSerializer(
            data={
                "name": "Payment Service",
                "description": "Updated description.",
                "canvas_data": {"nodes": [{"id": "n1"}]},
            }
        )
        assert s.is_valid(), s.errors

    def test_name_is_stripped(self):
        s = KnowledgeSpaceUpdateSerializer(data={"name": "  New Name  "})
        assert s.is_valid(), s.errors
        assert s.validated_data["name"] == "New Name"

    def test_invalid_missing_name(self):
        s = KnowledgeSpaceUpdateSerializer(data={"description": "no name"})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_invalid_blank_name(self):
        s = KnowledgeSpaceUpdateSerializer(data={"name": "  "})
        assert not s.is_valid()
        assert "name" in s.errors

    def test_canvas_data_absent_means_field_not_in_validated(self):
        """When canvas_data is not sent, it must be absent from validated_data
        so the service knows not to overwrite the existing canvas."""
        s = KnowledgeSpaceUpdateSerializer(data={"name": "Rename Only"})
        assert s.is_valid(), s.errors
        assert "canvas_data" not in s.validated_data

    def test_canvas_data_present_is_in_validated(self):
        s = KnowledgeSpaceUpdateSerializer(
            data={
                "name": "X",
                "canvas_data": {"nodes": []},
            }
        )
        assert s.is_valid(), s.errors
        assert "canvas_data" in s.validated_data

    def test_invalid_canvas_data_is_list(self):
        s = KnowledgeSpaceUpdateSerializer(data={"name": "X", "canvas_data": []})
        assert not s.is_valid()
        assert "canvas_data" in s.errors


# ─── KnowledgeSpaceListSerializer ────────────────────────────────────────────


@pytest.mark.django_db
class TestKnowledgeSpaceListSerializer:
    def test_output_excludes_canvas_data(self, knowledge_space):
        data = KnowledgeSpaceListSerializer(knowledge_space).data
        assert "canvas_data" not in data

    def test_output_contains_expected_fields(self, knowledge_space):
        data = KnowledgeSpaceListSerializer(knowledge_space).data
        expected = {
            "id",
            "workspace_id",
            "name",
            "description",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        }
        assert set(data.keys()) == expected

    def test_id_is_string_uuid(self, knowledge_space):
        data = KnowledgeSpaceListSerializer(knowledge_space).data
        uuid.UUID(data["id"])  # must parse without raising

    def test_workspace_id_matches(self, knowledge_space, workspace):
        data = KnowledgeSpaceListSerializer(knowledge_space).data
        assert uuid.UUID(data["workspace_id"]) == workspace.id

    def test_updated_by_is_null_for_new_space(self, knowledge_space):
        data = KnowledgeSpaceListSerializer(knowledge_space).data
        assert data["updated_by"] is None


# ─── KnowledgeSpaceSerializer (full) ─────────────────────────────────────────


@pytest.mark.django_db
class TestKnowledgeSpaceSerializer:
    def test_output_contains_canvas_data(self, knowledge_space):
        data = KnowledgeSpaceSerializer(knowledge_space).data
        assert "canvas_data" in data

    def test_output_contains_all_expected_fields(self, knowledge_space):
        data = KnowledgeSpaceSerializer(knowledge_space).data
        expected = {
            "id",
            "workspace_id",
            "name",
            "description",
            "canvas_data",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        }
        assert set(data.keys()) == expected

    def test_canvas_data_round_trips(self, knowledge_space):
        data = KnowledgeSpaceSerializer(knowledge_space).data
        assert data["canvas_data"] == {"nodes": [], "edges": []}

    def test_name_matches_fixture(self, knowledge_space):
        data = KnowledgeSpaceSerializer(knowledge_space).data
        assert data["name"] == "Authentication System"
