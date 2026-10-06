"""
Message search is the one read path that takes a predicate from the client.

`GET .../rooms/<room_pk>/messages/search/?q=...` hands `q` to the message store
and returns whatever matches. Everything a caller can learn from it is scoped
by the room in the URL and gated by `IsChatRoomMember`, and AUDIT case 10 asks
for that to be asserted rather than assumed: "room not discoverable via search,
asserted explicitly so the legacy/v2 split is a recorded decision, not an
accident".

Two things are being pinned:

  * who may run it -- for a DM, only its two participants. `IsChatRoomMember`
    special-cases `room_type == "dm"` and checks `ChatRoomParticipant`; every
    other room type falls through to workspace membership. That branch is the
    whole of the privacy story here, and no other test in this app reaches it.
  * what it is pointed at -- exactly the `room_pk` in the path. A search scoped
    to the workspace, or to some default room, would run the caller's predicate
    over conversations they cannot open.

The store itself is DynamoDB and there is none in CI, so `search_messages` is
patched throughout. That is deliberate rather than a compromise: the assertions
are about the arguments the view passes and the status it returns, which is
exactly what patching exposes. A test that let the real call through would be
asserting on a connection error.

Tests call the view with `user_id` set on the request, the same way `conftest`
does for DM creation -- see the note there on why `force_authenticate` would
make every one of them fail for the wrong reason.
"""

import pytest
import uuid
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from unittest.mock import patch

from apps.chat.services import ChatMessageService
from apps.chat.views.messages import MessageSearchView
from apps.workspaces.models import Workspace, WorkspaceMember

from .factories import DmRoomFactory, WorkspaceMemberFactory

# Touches the database for membership and room lookups; none can run without it.
pytestmark = pytest.mark.django_db


def search(
    api_factory: APIRequestFactory,
    workspace: Workspace,
    room_pk: uuid.UUID,
    caller: uuid.UUID,
    query: str = "deploy",
) -> Response:
    """Invoke the view the way the URLconf does.

    Same single line `conftest.post_dm` cannot type: `user_id` is attached by
    middleware and is not on DRF's `Request`, so the type checker is right to
    reject it and `setattr` is banned by ruff B010. The honest error stays, and
    it is the same one rather than a second variation on it.
    """
    factory_request = api_factory.get(
        f"/api/workspaces/{workspace.pk}/chat/rooms/{room_pk}/messages/search/",
        {"q": query},
        format="json",
    )
    factory_request.user_id = str(caller)
    view = MessageSearchView.as_view()
    return view(factory_request, workspace_pk=str(workspace.pk), room_pk=str(room_pk))


@pytest.fixture
def dm_room(workspace: Workspace) -> uuid.UUID:
    """A DM between the two members the `workspace` fixture creates."""
    members = list(WorkspaceMember.objects.filter(workspace=workspace))
    room = DmRoomFactory.create(
        workspace=workspace, participants=[members[0].user_id, members[1].user_id]
    )
    return room.pk


@pytest.fixture
def other_member(workspace: Workspace) -> uuid.UUID:
    """A third member of the same workspace, in neither half of `dm_room`."""
    return WorkspaceMemberFactory(workspace=workspace).user_id


class TestWhoMayRunASearch:
    def test_a_participant_may_search_their_own_conversation(
        self, api_factory, workspace, pair, dm_room
    ):
        caller, _ = pair

        with patch.object(
            ChatMessageService, "search_messages", return_value=[]
        ) as store:
            response = search(api_factory, workspace, dm_room, caller)

        # Pinned first so the refusals below cannot be satisfied by an endpoint
        # that refuses everybody.
        assert response.status_code == 200
        assert response.data == {"results": [], "count": 0}
        store.assert_called_once()

    def test_a_workspace_member_outside_the_conversation_cannot(
        self, api_factory, workspace, dm_room, other_member
    ):
        """Being in the workspace is not enough, and this is the only test that says so.

        Without the `room_type == "dm"` branch in `IsChatRoomMember`, this
        request falls through to the workspace-membership query, passes, and
        hands back message content from a conversation between two other
        people. That is the "room not discoverable via search" case.
        """
        with patch.object(ChatMessageService, "search_messages") as store:
            response = search(api_factory, workspace, dm_room, other_member)

        assert response.status_code == 403
        # Refused by the permission, so the store is never even asked -- which
        # is the difference between "not found" and "not run".
        store.assert_not_called()

    def test_someone_from_outside_the_workspace_cannot(
        self, api_factory, workspace, dm_room, stranger_id
    ):
        with patch.object(ChatMessageService, "search_messages") as store:
            response = search(api_factory, workspace, dm_room, stranger_id)

        assert response.status_code == 403
        store.assert_not_called()

    def test_a_room_that_does_not_exist_is_refused_not_acknowledged(
        self, api_factory, workspace, pair, dm_room
    ):
        """403 rather than 404, for the same reason the DM endpoint answers 403.

        The permission runs before the view and returns `False` when
        `ChatRoom.objects.get` raises, so `NotFound` in `_get_room` is never
        reached. A 404 here would confirm that a guessed room id exists.
        """
        caller, _ = pair

        response = search(api_factory, workspace, uuid.uuid4(), caller)

        assert response.status_code == 403


class TestWhatTheSearchIsPointedAt:
    def test_it_is_asked_about_the_room_in_the_url_and_no_other(
        self, api_factory, workspace, pair, dm_room
    ):
        """The scope is asserted as an argument, not as a result.

        A stub returning `[]` would pass a result assertion whether the view
        asked about this room or about the whole workspace; only the argument
        distinguishes them.
        """
        caller, _ = pair

        with patch.object(
            ChatMessageService, "search_messages", return_value=[]
        ) as store:
            search(api_factory, workspace, dm_room, caller, query="deploy")

        store.assert_called_once_with(room_id=str(dm_room), query="deploy")

    def test_a_too_short_query_never_reaches_the_store(
        self, api_factory, workspace, pair, dm_room
    ):
        """The length check sits *outside* the `try`, so it cannot become a 503.

        Worth pinning because a refactor moving validation after the store call
        would turn a client mistake into "message store temporarily
        unavailable", and the suite would stay green either way.
        """
        caller, _ = pair

        with patch.object(ChatMessageService, "search_messages") as store:
            response = search(api_factory, workspace, dm_room, caller, query="a")

        assert response.status_code == 400
        store.assert_not_called()


class TestWhenTheStoreIsUnavailable:
    def test_it_reports_the_documented_503_and_not_the_failure_itself(
        self, api_factory, workspace, pair, dm_room
    ):
        """The endpoint declares 503 in its own schema.

        The interesting assertion is the second one: the repository is
        DynamoDB, and a `ClientError` carries a table name and a request id.
        `ServiceUnavailable` is raised `from` it, so DRF's handler serialises
        only the declared message -- but that is a property of the exception
        hierarchy, not of luck, and it is what stops a storage detail reaching
        the client.
        """
        caller, _ = pair

        with patch.object(
            ChatMessageService,
            "search_messages",
            side_effect=RuntimeError("table chat-messages not found"),
        ):
            response = search(api_factory, workspace, dm_room, caller)

        assert response.status_code == 503
        assert "chat-messages" not in str(response.data)
