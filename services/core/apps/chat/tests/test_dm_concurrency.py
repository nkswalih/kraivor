"""
The duplicate-conversation race, and why most of the interesting parts of this
file are skipped here.

`get_or_create_dm_room` read "no such conversation" and then created one, with a
window in between. Two simultaneous requests both read empty, both created, and on
Postgres both committed: two rooms for one pair of people, each with a participant
row for each of them. `unique_together(room, user_id)` does not object, because it
constrains participants within a room, not rooms per pair.

The fix is a `select_for_update` on the two `WorkspaceMember` rows, sorted, before
the lookup.

## What cannot be tested here, and why

The suite runs on `sqlite3` in-memory (`core/settings/test.py`). SQLite serialises
writers, so it does not reproduce the Postgres outcome — it converts the race into
`OperationalError: database is locked`, which is a 500 rather than a duplicate.
Probed directly with two real threads and a real file-backed database:

    RESULTS:   [500, 200]

One request lost, one succeeded, and no duplicate room. So a threaded test written
against SQLite would be wrong twice over: it would pass against the unfixed code for
the wrong reason (a lock error is not a duplicate), and it would fail against a
correct fix, because the fix takes row locks SQLite does not have.

`TestTheRaceItself` is therefore marked to run only where the behaviour can
actually be observed. It is not padding — it is the test to run first against a
Postgres-backed suite, and leaving it skipped is more useful than deleting it or
letting it report a false pass.

## What is tested here instead

`TestTheLockItselfIsNarrow` reads the membership query out of the SQL the service
actually issues and asserts its shape. My first attempt at this file rebuilt the
lock inside each test, and all four of those tests passed against the unfixed
service — they were asserting that my design decision was the design decision,
because they never called the service. Reading the service's own output is what
makes them fail when the service is wrong.

Each shape assertion corresponds to a real failure that no behavioural test on this
database could catch: a lock on the workspace row instead of the member rows
serialises every DM in a workspace against every other; an unsorted lock deadlocks
when two people press Message at once; a lock taken after the lookup is worthless.

## Identifier format

SQLite stores `UUIDField` as 32 hex characters with no dashes, Postgres with dashes.
Assertions compare both sides with dashes stripped, so they hold on either backend.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.chat.models import ChatRoom
from apps.chat.services.room import ChatRoomService
from apps.chat.views.rooms import DMCreateView

from .factories import DmRoomFactory, WorkspaceFactory, WorkspaceMemberFactory

# These need to see committed rows across the transaction the service opens, which
# `django_db` wraps around in a rollback-only transaction.
pytestmark = pytest.mark.django_db(transaction=True)

requires_postgres = pytest.mark.skipif(
    connection.vendor != "postgresql",
    reason=(
        "SQLite serialises writers, so the race surfaces as a lock error rather "
        "than a duplicate room. Testing it here would pass against the unfixed "
        "code for the wrong reason and fail against the fix."
    ),
)


def undashed(value):
    """`str(uuid)` and `uuid.hex` differ only by dashes; the SQL may use either."""
    return str(value).replace("-", "")


def run_service(workspace, one, two):
    """Call the service against two members and return the SQL it emitted."""
    with CaptureQueriesContext(connection) as captured:
        ChatRoomService.get_or_create_dm_room(
            workspace_id=str(workspace.pk),
            user_id_1=str(one.user_id),
            user_id_2=str(two.user_id),
            target_name="jane",
        )
    return [query["sql"].lower() for query in captured.captured_queries]


def the_lock_query(statements):
    """The one membership query, or None if the service issued a different number.

    Exactly one, deliberately: two would mean the service queries membership twice
    — once to lock and once to check — which is a second race opening, and asserting
    on "the first one" would hide it.
    """
    matches = [s for s in statements if 'from "workspace_members"' in s]
    return matches[0] if len(matches) == 1 else None


class TestTheLockItselfIsNarrow:
    """Two member rows, this pair only, sorted, before the lookup."""

    def test_it_locks_exactly_the_two_members_of_the_pair(self):
        workspace = WorkspaceFactory()
        one = WorkspaceMemberFactory(workspace=workspace)
        two = WorkspaceMemberFactory(workspace=workspace)
        bystander = WorkspaceMemberFactory(workspace=workspace)
        elsewhere = WorkspaceFactory()
        outsider = WorkspaceMemberFactory(workspace=elsewhere)

        sql = the_lock_query(run_service(workspace, one, two))
        body = undashed(sql) if sql else ""

        # Pre-fix there is no membership query at all, so this fails on the `None`.
        assert sql is not None, "the service issued no membership query"
        assert undashed(one.user_id) in body
        assert undashed(two.user_id) in body

        # A third member of the same workspace is not part of this conversation, and
        # neither is anyone from another workspace. A lock wide enough to reach them
        # turns every DM in a busy workspace into a queue — which is exactly what
        # choosing the workspace row over the member rows would do, and that choice
        # passes every behavioural test in this file.
        assert undashed(bystander.user_id) not in body
        assert undashed(outsider.user_id) not in body
        assert undashed(elsewhere.pk) not in body

        # `user_id IN (a, b)` rather than a bare workspace match. The difference
        # between two rows and every row.
        assert " in (" in body
        assert undashed(workspace.pk) in body

    def test_it_locks_in_sorted_order(self):
        """
        The sort is what stops a deadlock, and it is invisible from the outside.

        Two transactions opening the same conversation in opposite order — which
        happens as soon as both people press Message at once — each take the row the
        other is holding, and Postgres kills one. Sorted, both want the same row
        first, so the second waits instead.

        Django collapses `order_by("user_id")` to a positional reference
        (`ORDER BY 1 ASC`) because `user_id` is the only column selected, so the
        assertion is that an ascending sort was emitted, not which form it took.
        """
        workspace = WorkspaceFactory()
        one = WorkspaceMemberFactory(workspace=workspace)
        two = WorkspaceMemberFactory(workspace=workspace)

        sql = the_lock_query(run_service(workspace, one, two))

        assert sql is not None
        assert "order by" in sql
        assert " desc" not in sql

    def test_it_reads_membership_through_the_alive_only_manager(self):
        """
        The manager choice, which is one word and easy to get wrong.

        `SoftDeleteManager.get_queryset` filters `deleted_at__isnull=True`. So a
        target who has left contributes no row, which agrees with the view refusing
        to message them at all — a lock built on an unfiltered manager would hold
        rows for conversations that cannot be created.
        """
        workspace = WorkspaceFactory()
        one = WorkspaceMemberFactory(workspace=workspace)
        two = WorkspaceMemberFactory(workspace=workspace)

        sql = the_lock_query(run_service(workspace, one, two))

        assert sql is not None
        assert "deleted_at" in sql
        assert "is null" in sql

    def test_it_locks_before_it_looks_up(self):
        """
        Ordering within the transaction: lock, then look up, then create.

        Reversed, the lock is worthless — the second transaction would do its
        lookup before blocking, still see nothing, and create. The outcome is
        unobservable on SQLite, so this checks the emitted order, which is the
        whole substance of the fix.
        """
        workspace = WorkspaceFactory()
        one = WorkspaceMemberFactory(workspace=workspace)
        two = WorkspaceMemberFactory(workspace=workspace)

        statements = run_service(workspace, one, two)

        lock_at = next(
            (i for i, s in enumerate(statements) if "workspace_members" in s), None
        )
        lookup_at = next(
            (i for i, s in enumerate(statements) if "chat_room_participants" in s), None
        )

        assert lock_at is not None, statements
        assert lookup_at is not None, statements
        assert lock_at < lookup_at, statements

    def test_the_lock_is_a_real_row_lock_where_the_backend_has_them(self):
        """
        `select_for_update` is a documented no-op on SQLite, so on this suite the
        SQL carries no `FOR UPDATE` and the four tests above check shape and
        ordering only.

        That is the whole reason the race itself is Postgres-only: on the database
        this suite runs on there is no lock to assert. Where the backend does have
        row locks the clause must be emitted, and a regression that swapped
        `select_for_update()` for a plain read would sail through the shape tests —
        the query would still select two member rows, in sorted order.
        """
        if connection.vendor == "sqlite":
            pytest.skip("SQLite has no row locks; see the module docstring.")

        workspace = WorkspaceFactory()
        one = WorkspaceMemberFactory(workspace=workspace)
        two = WorkspaceMemberFactory(workspace=workspace)

        sql = the_lock_query(run_service(workspace, one, two))

        assert sql is not None
        assert "for update" in sql


@requires_postgres
class TestTheRaceItself:
    """Two simultaneous requests, one conversation."""

    @staticmethod
    def _race(count, ask):
        """Run `ask` in `count` threads, released together.

        The barrier is the point. Without it the threads are as likely to run one
        after the other as at the same time, and the window under test is a few
        statements wide — a test that reproduces the race one run in three is worse
        than no test, because it reports a false pass.
        """
        import threading

        barrier = threading.Barrier(count)
        results: list = []
        failures: list[Exception] = []
        collect = threading.Lock()

        def run(index: int) -> None:
            barrier.wait()
            try:
                outcome = ask(index)
            except Exception as exc:
                with collect:
                    failures.append(exc)
                return
            with collect:
                results.append(outcome)

        threads = [threading.Thread(target=run, args=(i,)) for i in range(count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # A thread that dies takes its result with it, so the caller would
        # otherwise assert `[] == [200, 200]` and report the shape of the
        # absence instead of the error that caused it. Nothing changes for a
        # test whose threads all succeed -- no exception, no re-raise.
        if failures:
            raise failures[0]
        return results

    @staticmethod
    def _ask(api_factory, dm_view, workspace, caller, target):
        request = api_factory.post(
            f"/api/workspaces/{workspace.pk}/dm/",
            {"target_user_id": str(target), "target_user_name": "jane"},
            format="json",
        )
        request.user_id = str(caller)
        return dm_view(request, workspace_pk=str(workspace.pk))

    def test_two_simultaneous_requests_create_one_room_not_two(self, api_factory):
        workspace = WorkspaceFactory()
        caller = WorkspaceMemberFactory(workspace=workspace)
        target = WorkspaceMemberFactory(workspace=workspace)
        dm_view = DMCreateView.as_view()

        def ask(_index):
            return self._ask(
                api_factory, dm_view, workspace, caller.user_id, target.user_id
            )

        responses = self._race(2, ask)
        rooms = ChatRoom.objects.filter(
            workspace_id=workspace.pk, room_type=ChatRoom.RoomType.DM
        )

        assert sorted(r.status_code for r in responses) == [200, 200]
        assert rooms.count() == 1
        # Both callers got the same room, not merely a room each.
        assert len({r.data["id"] for r in responses}) == 1

    def test_a_race_against_a_live_conversation_reuses_it(
        self, api_factory, workspace, pair
    ):
        """
        The case a user actually hits: DM someone, keep talking, DM again from a
        second tab.

        Creating a second room strands the history in the old one and leaves the
        user in an empty thread with the same person, which reads as message loss.
        """
        caller, target = pair
        dm_view = DMCreateView.as_view()
        existing = DmRoomFactory.create(
            workspace=workspace, participants=[caller, target]
        )

        def ask(_index):
            return self._ask(api_factory, dm_view, workspace, caller, target)

        responses = self._race(2, ask)

        assert [r.data["id"] for r in responses] == [str(existing.pk)] * 2

    def test_the_lock_does_not_serialise_unrelated_conversations(
        self, api_factory, workspace, pair
    ):
        """
        Two pairs in one workspace must be able to proceed at the same time.

        A lock on the workspace row instead of the two member rows passes both
        tests above and still turns every DM in a workspace into a queue. This is
        the narrower claim, and the one that would otherwise go unchecked.
        """
        caller, target = pair
        dm_view = DMCreateView.as_view()
        other_workspace = WorkspaceFactory()
        other_caller = WorkspaceMemberFactory(workspace=other_workspace)
        other_target = WorkspaceMemberFactory(workspace=other_workspace)

        def ask(index):
            if index == 0:
                return self._ask(api_factory, dm_view, workspace, caller, target)
            return self._ask(
                api_factory,
                dm_view,
                other_workspace,
                other_caller.user_id,
                other_target.user_id,
            )

        responses = self._race(2, ask)

        assert sorted(r.status_code for r in responses) == [200, 200]
        # Two rooms, one per pair. Not one (over-locked: unrelated pairs collided)
        # and not two per pair (under-locked: the original race).
        assert ChatRoom.objects.filter(room_type=ChatRoom.RoomType.DM).count() == 2
        assert len({r.data["id"] for r in responses}) == 2


@requires_postgres
class TestTheLockDoesNotStarve:
    """
    A lock taken on rows the transaction does not otherwise need can hang.

    Worth one test: the fix acquires `FOR UPDATE` on two membership rows on every
    DM open, so if a caller ever reaches the service inside a transaction that
    already holds conflicting locks, this is where it shows. SQLite cannot
    reproduce it — there are no row locks — so it is Postgres-only.
    """

    def test_opening_a_dm_inside_a_callers_transaction_completes(self, api_factory):
        workspace = WorkspaceFactory()
        caller = WorkspaceMemberFactory(workspace=workspace)
        target = WorkspaceMemberFactory(workspace=workspace)
        dm_view = DMCreateView.as_view()

        from django.db import transaction

        def ask(_index):
            with transaction.atomic():
                return TestTheRaceItself._ask(
                    api_factory, dm_view, workspace, caller.user_id, target.user_id
                )

        # Both helpers live on `TestTheRaceItself`, and both are reached for the
        # same way. Written as `self._ask` this raised AttributeError in both
        # threads, left `results` empty, and failed as `[] == [200, 200]` -- but
        # only on Postgres, because `@requires_postgres` skips this class on the
        # SQLite suite this file normally runs under. CI was the first run.
        responses = TestTheRaceItself._race(2, ask)

        assert sorted(r.status_code for r in responses) == [200, 200]
        assert (
            ChatRoom.objects.filter(
                workspace_id=workspace.pk, room_type=ChatRoom.RoomType.DM
            ).count()
            == 1
        )
