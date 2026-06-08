"""
Knowledge Space view tests — KRV-022.

Strategy: APIRequestFactory with request.user_id set directly on the raw
WSGIRequest, bypassing JWTAuthenticationMiddleware. DRF's Request.__getattr__
delegates to _request so user_id is accessible on the wrapped request.

Soft-delete note:
  After DELETE calls, check knowledge_space.is_deleted on the in-memory
  instance — do NOT call refresh_from_db() (raises DoesNotExist because
  SoftDeleteManager excludes deleted rows from the default queryset).

Views under test:
  KnowledgeSpaceListCreateView — GET list (with/without search), POST create
  KnowledgeSpaceDetailView     — GET retrieve, PUT update, DELETE delete

Scenarios per view:
  - Authentication guard (missing user_id → 403)
  - Workspace membership (non-member → 404)
  - Role-based access (viewer → 403 for writes, 200 for reads)
  - Success status codes and response shapes
  - Input validation (400 on bad payloads)
  - Service exception → HTTP status code mapping
"""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory

from apps.knowledge.models import KnowledgeSpace
from apps.knowledge.views import KnowledgeSpaceDetailView, KnowledgeSpaceListCreateView

from .conftest import make_request

# ─── GET /workspaces/{workspace_pk}/knowledge/ ────────────────────────────────


@pytest.mark.django_db
class TestKnowledgeSpaceListView:
    def _call(self, workspace, user_id, data=None):
        request = make_request("get", "/api/workspaces/x/knowledge/", user_id, data=data)
        return KnowledgeSpaceListCreateView.as_view()(request, workspace_pk=workspace.id)

    def test_returns_200_for_owner(self, workspace, owner_member, owner_id):
        assert self._call(workspace, owner_id).status_code == status.HTTP_200_OK

    def test_returns_200_for_admin(self, workspace, admin_member, admin_id):
        assert self._call(workspace, admin_id).status_code == status.HTTP_200_OK

    def test_returns_200_for_member(self, workspace, regular_member, member_id):
        assert self._call(workspace, member_id).status_code == status.HTTP_200_OK

    def test_returns_200_for_viewer(self, workspace, viewer_member, viewer_id):
        """Viewers can list — all roles have read access."""
        assert self._call(workspace, viewer_id).status_code == status.HTTP_200_OK

    def test_returns_knowledge_space_list(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        response = self._call(workspace, owner_id)
        assert len(response.data) == 1
        assert response.data[0]["name"] == knowledge_space.name

    def test_list_excludes_canvas_data(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        """List response uses KnowledgeSpaceListSerializer — no canvas_data."""
        response = self._call(workspace, owner_id)
        assert "canvas_data" not in response.data[0]

    def test_returns_empty_list_when_no_spaces(self, workspace, owner_member, owner_id):
        response = self._call(workspace, owner_id)
        assert response.data == []

    def test_excludes_deleted_spaces(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        knowledge_space.delete()
        response = self._call(workspace, owner_id)
        assert response.data == []

    def test_returns_404_for_non_member(self, workspace, outsider_id):
        assert self._call(workspace, outsider_id).status_code == status.HTTP_404_NOT_FOUND

    def test_returns_403_without_user_id(self, workspace):
        raw = APIRequestFactory().get("/api/workspaces/x/knowledge/", format="json")
        # Deliberately omit raw.user_id
        response = KnowledgeSpaceListCreateView.as_view()(raw, workspace_pk=workspace.id)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # ── Search ────────────────────────────────────────────────────────────────

    def test_search_filters_by_name(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        # knowledge_space.name = "Authentication System"
        response = self._call(workspace, owner_id, data={"search": "Authentication"})
        assert len(response.data) == 1

    def test_search_returns_empty_for_no_match(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        response = self._call(workspace, owner_id, data={"search": "zzznomatch"})
        assert response.data == []

    def test_search_filters_by_description(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        # knowledge_space.description = "Diagrams and notes about the auth flow."
        response = self._call(workspace, owner_id, data={"search": "diagrams"})
        assert len(response.data) == 1

    def test_empty_search_returns_all(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        response = self._call(workspace, owner_id, data={"search": ""})
        assert len(response.data) == 1


# ─── POST /workspaces/{workspace_pk}/knowledge/ ───────────────────────────────


@pytest.mark.django_db
class TestKnowledgeSpaceCreateView:
    _PAYLOAD = {"name": "Payment Service"}

    def _call(self, workspace, user_id, data=None):
        request = make_request(
            "post",
            "/api/workspaces/x/knowledge/",
            user_id,
            data=data if data is not None else self._PAYLOAD,
        )
        return KnowledgeSpaceListCreateView.as_view()(request, workspace_pk=workspace.id)

    def test_returns_201_for_owner(self, workspace, owner_member, owner_id):
        assert self._call(workspace, owner_id).status_code == status.HTTP_201_CREATED

    def test_returns_201_for_admin(self, workspace, admin_member, admin_id):
        assert self._call(workspace, admin_id).status_code == status.HTTP_201_CREATED

    def test_returns_201_for_member(self, workspace, regular_member, member_id):
        assert self._call(workspace, member_id).status_code == status.HTTP_201_CREATED

    def test_response_includes_canvas_data(self, workspace, owner_member, owner_id):
        """Create response uses full KnowledgeSpaceSerializer — canvas_data included."""
        response = self._call(workspace, owner_id)
        assert "canvas_data" in response.data

    def test_response_name_matches_input(self, workspace, owner_member, owner_id):
        response = self._call(workspace, owner_id, data={"name": "Sprint Planning"})
        assert response.data["name"] == "Sprint Planning"

    def test_response_workspace_id_matches(self, workspace, owner_member, owner_id):
        response = self._call(workspace, owner_id)
        assert uuid.UUID(response.data["workspace_id"]) == workspace.id

    def test_creates_with_canvas_data(self, workspace, owner_member, owner_id):
        canvas = {"nodes": [{"id": "n1", "type": "text"}]}
        response = self._call(workspace, owner_id, data={"name": "X", "canvas_data": canvas})
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["canvas_data"] == canvas

    def test_returns_403_for_viewer(self, workspace, viewer_member, viewer_id):
        assert self._call(workspace, viewer_id).status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_non_member(self, workspace, outsider_id):
        assert self._call(workspace, outsider_id).status_code == status.HTTP_404_NOT_FOUND

    def test_returns_400_for_missing_name(self, workspace, owner_member, owner_id):
        response = self._call(workspace, owner_id, data={})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in response.data

    def test_returns_400_for_blank_name(self, workspace, owner_member, owner_id):
        response = self._call(workspace, owner_id, data={"name": "   "})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_returns_400_for_canvas_data_as_list(self, workspace, owner_member, owner_id):
        response = self._call(workspace, owner_id, data={"name": "X", "canvas_data": [1, 2]})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "canvas_data" in response.data


# ─── GET /knowledge/{pk}/ ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestKnowledgeSpaceRetrieveView:
    def _call(self, user_id, pk):
        request = make_request("get", f"/api/knowledge/{pk}/", user_id)
        return KnowledgeSpaceDetailView.as_view()(request, pk=pk)

    def test_returns_200_for_owner(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        assert self._call(owner_id, knowledge_space.id).status_code == status.HTTP_200_OK

    def test_returns_200_for_viewer(
        self,
        workspace,
        viewer_member,
        viewer_id,
        knowledge_space,
    ):
        """Viewers can retrieve — all roles have read access."""
        assert self._call(viewer_id, knowledge_space.id).status_code == status.HTTP_200_OK

    def test_response_includes_canvas_data(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        response = self._call(owner_id, knowledge_space.id)
        assert "canvas_data" in response.data
        assert response.data["canvas_data"] == knowledge_space.canvas_data

    def test_response_contains_all_fields(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        response = self._call(owner_id, knowledge_space.id)
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
        assert set(response.data.keys()) == expected

    def test_returns_404_for_non_member(self, workspace, outsider_id, knowledge_space):
        assert self._call(outsider_id, knowledge_space.id).status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_for_soft_deleted_space(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        knowledge_space.delete()
        assert self._call(owner_id, knowledge_space.id).status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_for_nonexistent_id(self, workspace, owner_member, owner_id):
        assert self._call(owner_id, uuid.uuid4()).status_code == status.HTTP_404_NOT_FOUND

    def test_returns_403_without_user_id(self, workspace, knowledge_space):
        raw = APIRequestFactory().get(f"/api/knowledge/{knowledge_space.id}/", format="json")
        response = KnowledgeSpaceDetailView.as_view()(raw, pk=knowledge_space.id)
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ─── PUT /knowledge/{pk}/ ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestKnowledgeSpaceUpdateView:
    _PAYLOAD = {"name": "Updated Name"}

    def _call(self, user_id, pk, data=None):
        request = make_request(
            "put",
            f"/api/knowledge/{pk}/",
            user_id,
            data=data or self._PAYLOAD,
        )
        return KnowledgeSpaceDetailView.as_view()(request, pk=pk)

    def test_returns_200_for_owner(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        assert self._call(owner_id, knowledge_space.id).status_code == status.HTTP_200_OK

    def test_returns_200_for_admin(
        self,
        workspace,
        admin_member,
        admin_id,
        knowledge_space,
    ):
        assert self._call(admin_id, knowledge_space.id).status_code == status.HTTP_200_OK

    def test_returns_200_for_member(
        self,
        workspace,
        regular_member,
        member_id,
        knowledge_space,
    ):
        assert self._call(member_id, knowledge_space.id).status_code == status.HTTP_200_OK

    def test_response_reflects_updated_name(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        response = self._call(owner_id, knowledge_space.id, data={"name": "New Name"})
        assert response.data["name"] == "New Name"

    def test_response_includes_canvas_data(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        response = self._call(owner_id, knowledge_space.id)
        assert "canvas_data" in response.data

    def test_updates_canvas_data(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        new_canvas = {"nodes": [{"id": "sticky-1", "type": "sticky_note"}]}
        response = self._call(
            owner_id,
            knowledge_space.id,
            data={"name": "X", "canvas_data": new_canvas},
        )
        assert response.data["canvas_data"] == new_canvas

    def test_returns_403_for_viewer(
        self,
        workspace,
        viewer_member,
        viewer_id,
        knowledge_space,
    ):
        assert self._call(viewer_id, knowledge_space.id).status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_non_member(self, workspace, outsider_id, knowledge_space):
        assert self._call(outsider_id, knowledge_space.id).status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_for_soft_deleted_space(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        knowledge_space.delete()
        assert self._call(owner_id, knowledge_space.id).status_code == status.HTTP_404_NOT_FOUND

    def test_returns_400_for_missing_name(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        response = self._call(owner_id, knowledge_space.id, data={"description": "no name"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "name" in response.data

    def test_returns_400_for_canvas_data_as_list(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        response = self._call(
            owner_id,
            knowledge_space.id,
            data={"name": "X", "canvas_data": ["not", "a", "dict"]},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ─── DELETE /knowledge/{pk}/ ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestKnowledgeSpaceDeleteView:
    def _call(self, user_id, pk):
        request = make_request("delete", f"/api/knowledge/{pk}/", user_id)
        return KnowledgeSpaceDetailView.as_view()(request, pk=pk)

    def test_returns_204_for_owner(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        assert self._call(owner_id, knowledge_space.id).status_code == status.HTTP_204_NO_CONTENT

    def test_returns_204_for_admin(
        self,
        workspace,
        admin_member,
        admin_id,
        knowledge_space,
    ):
        assert self._call(admin_id, knowledge_space.id).status_code == status.HTTP_204_NO_CONTENT

    def test_space_is_soft_deleted_after_call(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        """
        The view loads a new Python object via _get_knowledge_space_or_404(),
        so the fixture variable is not mutated. Refetch from all_objects to
        verify the soft delete was persisted to the DB transaction.
        """
        self._call(owner_id, knowledge_space.id)
        ks = KnowledgeSpace.all_objects.get(id=knowledge_space.id)
        assert ks.is_deleted

    def test_returns_403_for_member(
        self,
        workspace,
        regular_member,
        member_id,
        knowledge_space,
    ):
        assert self._call(member_id, knowledge_space.id).status_code == status.HTTP_403_FORBIDDEN

    def test_returns_403_for_viewer(
        self,
        workspace,
        viewer_member,
        viewer_id,
        knowledge_space,
    ):
        assert self._call(viewer_id, knowledge_space.id).status_code == status.HTTP_403_FORBIDDEN

    def test_returns_404_for_non_member(self, workspace, outsider_id, knowledge_space):
        """
        Non-members receive 404 (not 403) — avoids leaking that the
        knowledge space exists at this ID.
        """
        assert self._call(outsider_id, knowledge_space.id).status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_for_already_deleted_space(
        self,
        workspace,
        owner_member,
        owner_id,
        knowledge_space,
    ):
        knowledge_space.delete()
        assert self._call(owner_id, knowledge_space.id).status_code == status.HTTP_404_NOT_FOUND

    def test_returns_404_for_nonexistent_id(self, workspace, owner_member, owner_id):
        assert self._call(owner_id, uuid.uuid4()).status_code == status.HTTP_404_NOT_FOUND
