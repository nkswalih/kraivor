"""
`POST /dm/` validated nothing about who it was messaging.

`DMCreateView.post` takes `target_user_id` and `target_user_name` from the client,
hands them to `get_or_create_dm_room`, and returns whatever comes back. Five
things follow, and every test here is one of them.

The tests call the view with `user_id` set on the request rather than
authenticating a Django user, because that is what `IsChatRoomMember` and the view
both read. See `conftest`.

Test methods take their fixtures unannotated, matching every other test module in
this service -- `apps/community/tests` and `apps/workspaces/tests` report the same
`no-untyped-def` on each one.
"""

import pytest

from apps.chat.models import ChatRoom, ChatRoomParticipant
from apps.workspaces.models import WorkspaceMember

from .conftest import post_dm
from .factories import DmRoomFactory, WorkspaceFactory, WorkspaceMemberFactory

# Every test here touches the database and none can run without it: the endpoint
# reads membership and writes rooms. Module level rather than per test, because
# forgetting one is a test that fails for a reason unrelated to what it tests.
pytestmark = pytest.mark.django_db


def participant_ids(room_id):
    return {
        str(user_id)
        for user_id in ChatRoomParticipant.objects.filter(room_id=room_id).values_list(
            "user_id", flat=True
        )
    }


def dm_room_count():
    return ChatRoom.objects.filter(room_type=ChatRoom.RoomType.DM).count()


class TestTheTargetIsSomebodyYouCanMessage:
    """The caller was checked for workspace membership. The target was not."""

    def test_a_workspace_member_can_be_messaged(
        self, api_factory, dm_view, workspace, pair
    ):
        caller, target = pair

        response = post_dm(api_factory, dm_view, workspace, caller, target)

        # The happy path, pinned first so the rejections below cannot be satisfied
        # by an endpoint that refuses everybody.
        assert response.status_code == 200
        room = ChatRoom.objects.get(id=response.data["id"])
        assert room.room_type == ChatRoom.RoomType.DM
        assert participant_ids(room.id) == {str(caller), str(target)}

    def test_a_user_who_is_not_in_the_workspace_is_refused(
        self, api_factory, dm_view, workspace, pair, stranger_id
    ):
        caller, _ = pair

        # Before this, a room was created with a participant row for a user id
        # belonging to nobody. The other participant's sidebar then rendered a DM
        # to someone who does not exist, and no later request could make it work.
        response = post_dm(api_factory, dm_view, workspace, caller, stranger_id)

        assert response.status_code == 403
        assert dm_room_count() == 0

    def test_a_removed_member_is_refused(self, api_factory, dm_view, workspace, pair):
        caller, target = pair
        WorkspaceMember.objects.filter(workspace=workspace, user_id=target).delete()

        # `delete()` on the soft-delete manager sets `deleted_at`, which is this
        # codebase's "no longer here". The caller's own check goes through
        # `WorkspaceMember.objects`, whose queryset is already `.alive()` -- so
        # using the same manager for the target is what makes these the same
        # check. Somebody who left could still be handed a DM room.
        response = post_dm(api_factory, dm_view, workspace, caller, target)

        assert response.status_code == 403
        assert dm_room_count() == 0

    def test_a_member_of_another_workspace_is_refused(
        self, api_factory, dm_view, workspace, pair
    ):
        caller, _ = pair
        outsider = WorkspaceMemberFactory(workspace=WorkspaceFactory()).user_id

        # Distinct from "does not exist", and it is what a workspace-scoped query
        # gets wrong when written against the wrong table. Core holds no users
        # table -- only cross-service `user_id` references -- so `WorkspaceMember`
        # is the only thing that knows who belongs where.
        response = post_dm(api_factory, dm_view, workspace, caller, outsider)

        assert response.status_code == 403
        assert dm_room_count() == 0

    def test_all_three_refusals_say_the_same_thing(
        self, api_factory, dm_view, workspace, pair, stranger_id
    ):
        """Refusing them differently would turn the endpoint into a user directory.

        A 404 for "no such user" beside a 403 for "not in your workspace" is a
        reliable oracle: post any UUID and learn whether it belongs to an account.
        One code for one reason, and a body that names none of them.
        """
        caller, target = pair
        WorkspaceMember.objects.filter(workspace=workspace, user_id=target).delete()
        outsider = WorkspaceMemberFactory(workspace=WorkspaceFactory()).user_id

        unknown = post_dm(api_factory, dm_view, workspace, caller, stranger_id)
        gone = post_dm(api_factory, dm_view, workspace, caller, target)
        foreign = post_dm(api_factory, dm_view, workspace, caller, outsider)

        assert {unknown.status_code, gone.status_code, foreign.status_code} == {403}
        assert unknown.data == gone.data == foreign.data


class TestYouCannotMessageYourself:
    """
    The one case that was a 500.

    `get_or_create_dm_room` finds an existing conversation by counting participants
    whose id is in `[user_id_1, user_id_2]`. With the two equal that `cnt=2` can
    never match -- one user, one row -- so the lookup always fell through to
    creating a room and inserting the *same* participant twice.
    `ChatRoomParticipant` has `unique_together(room, user_id)`, and that
    `bulk_create` has no `ignore_conflicts` (unlike the group-room path in the same
    file), so the insert raised `IntegrityError` and the client got a 500 for asking
    a question with an obvious answer.
    """

    def test_it_is_rejected_rather_than_crashing(
        self, api_factory, dm_view, workspace, pair
    ):
        caller, _ = pair

        response = post_dm(api_factory, dm_view, workspace, caller, caller)

        # 400, not 403: nobody was forbidden, the request itself cannot be
        # satisfied. And not a 200 with an empty room either -- "a conversation with
        # yourself" is not something the rest of the app can render, so it must not
        # be created and then discovered to be unusable.
        assert response.status_code == 400
        assert dm_room_count() == 0

    def test_it_leaves_no_half_built_room_behind(
        self, api_factory, dm_view, workspace, pair
    ):
        """The 500 came *after* `ChatRoom.objects.create` had been issued.

        `@transaction.atomic` rolls that insert back, so this passes today by
        accident -- and keeps passing for the wrong reason once the request is
        rejected before the service is reached. Asserted anyway because the room is
        created before its participants: an exit between the two leaves a room
        nobody is a member of, which `list_rooms` never shows and nothing cleans up.
        """
        caller, _ = pair
        before = set(ChatRoom.objects.values_list("id", flat=True))

        post_dm(api_factory, dm_view, workspace, caller, caller)

        assert set(ChatRoom.objects.values_list("id", flat=True)) == before


class TestTheRoomName:
    """
    Regression guards, not fixes. `CreateDmSerializer` already handles all of it --
    `CharField(max_length=255)`, `.strip()`, and a non-blank check
    (`room_serializers.py:152-160`).

    Worth pinning anyway, because the fix beside this adds validation *in the view*
    and it would be easy for that to read the raw request instead of
    `validated_data`, taking the blank and over-length cases back to the 500s the
    serializer is currently the only thing preventing.
    """

    def test_a_blank_name_is_refused(self, api_factory, dm_view, workspace, pair):
        caller, target = pair

        response = post_dm(api_factory, dm_view, workspace, caller, target, name="   ")

        assert response.status_code == 400
        assert dm_room_count() == 0

    def test_a_name_longer_than_the_column_is_refused(
        self, api_factory, dm_view, workspace, pair
    ):
        caller, target = pair

        # Postgres raises `StringDataRightTruncation` rather than truncating, so a
        # view reading the raw request here would make this a driver-dependent 500.
        response = post_dm(
            api_factory, dm_view, workspace, caller, target, name="x" * 256
        )

        assert response.status_code == 400
        assert dm_room_count() == 0

    def test_a_name_is_stored_trimmed(self, api_factory, dm_view, workspace, pair):
        caller, target = pair

        response = post_dm(
            api_factory, dm_view, workspace, caller, target, name=" jane "
        )

        # Pinned because the sidebar sorts rooms by `(last_message_at, name)` and
        # renders the name verbatim, so an untrimmed name is a visible difference
        # between two conversations -- and one that survives a reload.
        assert response.status_code == 200
        assert ChatRoom.objects.get(id=response.data["id"]).name == "jane"

    def test_the_target_name_is_what_the_room_is_called(
        self, api_factory, dm_view, workspace, pair
    ):
        """Naming the room is the one thing a DM creator gets to choose.

        Not a bug: both participants see one room name, and the convention is the
        target's -- the only name the *target* can recognise. Pinned because it
        would be easy to "fix" by overwriting it with something derived during a
        later refactor, and this is deliberate.
        """
        caller, target = pair

        response = post_dm(api_factory, dm_view, workspace, caller, target, name="jane")

        assert ChatRoom.objects.get(id=response.data["id"]).name == "jane"


class TestReachingAnExistingConversation:
    """`get_or_create` is the endpoint's whole purpose, and nothing covered it."""

    def test_a_second_request_returns_the_same_room(
        self, api_factory, dm_view, workspace, pair
    ):
        caller, target = pair

        first = post_dm(api_factory, dm_view, workspace, caller, target)
        second = post_dm(api_factory, dm_view, workspace, caller, target)

        assert first.data["id"] == second.data["id"]
        assert dm_room_count() == 1

    def test_it_does_not_depend_on_who_asks(
        self, api_factory, dm_view, workspace, pair
    ):
        """The lookup filters `user_id__in=[u1, u2]`, so it should be order-free.

        Worth pinning rather than assuming: it is a filter over a list, and a
        regression narrowing it to `user_id=user_id_1` would still pass every test
        where one person starts both conversations -- which is what the frontend
        does, so the suite would stay green while the app broke.
        """
        caller, target = pair

        forwards = post_dm(api_factory, dm_view, workspace, caller, target)
        backwards = post_dm(api_factory, dm_view, workspace, target, caller)

        assert forwards.data["id"] == backwards.data["id"]
        assert dm_room_count() == 1

    def test_an_existing_conversation_is_not_re_renamed(
        self, api_factory, dm_view, workspace, pair
    ):
        caller, target = pair
        first = post_dm(api_factory, dm_view, workspace, caller, target, name="jane")

        second = post_dm(
            api_factory, dm_view, workspace, caller, target, name="renamed"
        )

        # The lookup returns the room and never touches `name`, so this already
        # holds. Asserted because the validation added in this change reads the
        # name *before* deciding whether to look for an existing room, which makes
        # it possible to apply on the way out by accident.
        assert second.data["id"] == first.data["id"]
        assert ChatRoom.objects.get(id=first.data["id"]).name == "jane"

    def test_an_archived_room_is_not_resurrected(
        self, api_factory, dm_view, workspace, pair
    ):
        """
        A decision, recorded so it is not mistaken for an oversight.

        The lookup filters `room__is_active=True`, so archiving a DM and asking for
        it again produces a *second* room: the history is orphaned on the archived
        row and the user starts from empty.

        The alternative -- un-archiving -- would mean a "delete" that does not
        delete, and would let either participant reverse the other's decision by
        opening a DM. Which of those is wanted is a product question, so this pins
        the current behaviour rather than changing it. What would be wrong is
        leaving it unspecified.
        """
        caller, target = pair
        first = post_dm(api_factory, dm_view, workspace, caller, target)
        ChatRoom.objects.filter(id=first.data["id"]).update(is_active=False)

        second = post_dm(api_factory, dm_view, workspace, caller, target)

        assert second.data["id"] != first.data["id"]
        assert dm_room_count() == 2

    def test_an_existing_room_built_directly_is_still_found(
        self, api_factory, dm_view, workspace, pair
    ):
        """The lookup counts participants, so it must not care how the room was made.

        Rooms created by a migration or a backfill are indistinguishable from ones
        this endpoint made, and there is nothing in the schema that says otherwise.
        Pinning it means a later "simplification" to a two-column join cannot
        quietly exclude them.
        """
        caller, target = pair
        existing = DmRoomFactory.create(
            workspace=workspace, participants=[caller, target]
        )

        response = post_dm(api_factory, dm_view, workspace, caller, target)

        assert response.data["id"] == str(existing.pk)
        assert dm_room_count() == 1
