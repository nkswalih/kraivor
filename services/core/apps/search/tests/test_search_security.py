"""
Security tests for the search app.

Two vulnerabilities are covered here:

1. CROSS-WORKSPACE IDOR — SearchView took the target workspace straight from
   the `workspace` query parameter and passed it to the search service without
   any membership check. Any authenticated user could read another workspace's
   projects, tasks, knowledge assets, repositories and notifications by ID.

2. UNSCOPED CHAT SEARCH — search_chat() enumerated chat rooms with no
   authorization boundary at all, and additionally called the DynamoDB
   repository with the wrong argument order, so it raised TypeError and was
   swallowed by a bare `except Exception` — chat search silently returned
   nothing, ever.
"""

import pytest
import uuid
from rest_framework.exceptions import NotFound
from unittest.mock import patch

pytestmark = pytest.mark.security


class TestSearchWorkspaceIsolation:
    """The `workspace` query param is attacker-controlled."""

    def _request(self, request_factory, workspace_id, user_id, query="secret"):
        from rest_framework.request import Request

        raw = request_factory.get(
            "/api/search/", {"q": query, "workspace": str(workspace_id)}
        )
        # The view reads request.query_params, which only exists on a DRF
        # Request — RequestFactory gives us a plain WSGIRequest.
        request = Request(raw)
        request.user_id = user_id
        return request

    def test_non_member_is_rejected(self, request_factory, workspace, outsider):
        from apps.search.views import SearchView

        request = self._request(request_factory, workspace.id, outsider)

        with pytest.raises(NotFound):
            SearchView().get(request)

    def test_non_member_never_reaches_the_search_service(
        self, request_factory, workspace, outsider
    ):
        """The guard must run BEFORE any query is issued."""
        from apps.search.views import SearchView

        request = self._request(request_factory, workspace.id, outsider)

        with (
            patch("apps.search.views.SearchService") as service,
            pytest.raises(NotFound),
        ):
            SearchView().get(request)

        service.assert_not_called()

    def test_member_is_allowed(self, request_factory, workspace, member):
        from apps.search.views import SearchView

        request = self._request(
            request_factory, workspace.id, member.user_id, query="roadmap"
        )

        with patch("apps.search.views.SearchService") as service:
            service.return_value.search.return_value = {
                "query": "roadmap",
                "total_results": 0,
                "page": 1,
                "page_size": 20,
                "results": [],
                "facets": {},
            }
            response = SearchView().get(request)

        assert response.status_code == 200
        service.return_value.search.assert_called_once()
        assert service.return_value.search.call_args.kwargs["user_id"] == str(
            member.user_id
        )

    def test_soft_deleted_member_is_rejected(self, request_factory, workspace, member):
        """A removed member must not retain search access."""
        from apps.search.views import SearchView

        member.delete()
        request = self._request(
            request_factory, workspace.id, member.user_id, query="roadmap"
        )

        with pytest.raises(NotFound):
            SearchView().get(request)

    def test_unknown_workspace_is_rejected(self, request_factory, member):
        from apps.search.views import SearchView

        request = self._request(request_factory, uuid.uuid4(), member.user_id)

        with pytest.raises(NotFound):
            SearchView().get(request)


class TestChatSearchScoping:
    """Chat search must only ever touch rooms the caller belongs to."""

    def test_no_user_id_yields_no_rooms(self):
        from apps.search.services import _searchable_room_ids

        assert _searchable_room_ids(None, "some-workspace") == []

    def test_returns_only_rooms_the_user_belongs_to(self, workspace, member, db):
        from apps.chat.models import Room, RoomMember
        from apps.search.services import _searchable_room_ids

        mine = Room.objects.create(
            name="My DM", room_type=Room.RoomType.DM, created_by=member.user_id
        )
        RoomMember.objects.create(room=mine, user_id=member.user_id)

        theirs = Room.objects.create(
            name="Someone Elses DM", room_type=Room.RoomType.DM, created_by=uuid.uuid4()
        )
        RoomMember.objects.create(room=theirs, user_id=uuid.uuid4())

        room_ids = _searchable_room_ids(str(member.user_id), str(workspace.id))

        assert str(mine.id) in room_ids
        assert str(theirs.id) not in room_ids

    def test_respects_the_cap(self, workspace, member, db):
        from apps.chat.models import Room, RoomMember
        from apps.search.services import _searchable_room_ids

        for _ in range(30):
            room = Room.objects.create(
                name="Room", room_type=Room.RoomType.GROUP, created_by=member.user_id
            )
            RoomMember.objects.create(room=room, user_id=member.user_id)

        room_ids = _searchable_room_ids(str(member.user_id), str(workspace.id), cap=5)

        assert len(room_ids) == 5

    def test_search_messages_receives_room_id_and_query(self, workspace, member, db):
        """
        Regression: search_chat called repo.search_messages(query, limit=...)
        but the signature is (room_id, query, limit). The query was passed as
        the room id, raising TypeError that a bare `except Exception` swallowed.
        """
        from apps.chat.models import Room, RoomMember
        from apps.search.services import search_chat

        room = Room.objects.create(
            name="Ops DM", room_type=Room.RoomType.DM, created_by=member.user_id
        )
        RoomMember.objects.create(room=room, user_id=member.user_id)

        with patch("apps.chat.dynamodb.search_messages") as mock_search:
            mock_search.return_value = [
                {
                    "message_id": "m1",
                    "content": "deploy failed on prod",
                    "sender_name": "Ada",
                    "created_at": "2026-01-01T00:00:00Z",
                }
            ]
            results = search_chat(
                "deploy", str(workspace.id), user_id=str(member.user_id)
            )

        mock_search.assert_called_once_with(str(room.id), "deploy", limit=10)
        assert len(results) == 1
        assert results[0].type == "chat"
        assert results[0].metadata["room_id"] == str(room.id)

    def test_short_query_short_circuits(self, workspace, member, db):
        from apps.search.services import search_chat

        assert search_chat("d", str(workspace.id), user_id=str(member.user_id)) == []
