import factory
import factory.django
import uuid

from apps.chat.models import ChatRoom, ChatRoomParticipant
from apps.workspaces.constants import WorkspaceRole
from apps.workspaces.models import Workspace, WorkspaceMember

# Deliberately mirrors `apps/community/tests/factories.py` and
# `apps/workspaces/tests/factories.py` rather than being stricter than them.
#
# `factory_boy` has no type stubs, so every `factory.Sequence`, `factory.SubFactory`
# and `DjangoModelFactory` here is `attr-defined` / `type-arg` to mypy. That is
# true of every factory in the service and chasing it here would make this file
# the only one of its kind in the tree. Annotating the two return types is the
# part that costs nothing, and `workspace: WorkspaceFactory` on `conftest.workspace`
# is really `Workspace`.


class WorkspaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workspace

    owner_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Test Workspace {n}")
    slug = factory.Sequence(lambda n: f"test-workspace-{n}")


class WorkspaceMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkspaceMember

    workspace = factory.SubFactory(WorkspaceFactory)
    user_id = factory.LazyFunction(uuid.uuid4)
    role = WorkspaceRole.MEMBER


class ChatRoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ChatRoom

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f"room-{n}")
    room_type = ChatRoom.RoomType.GROUP
    created_by = factory.LazyFunction(uuid.uuid4)


class DmRoomFactory(factory.django.DjangoModelFactory):
    """A DM room with both participants, which is what the lookup expects to find."""

    class Meta:
        model = ChatRoom

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f"dm-{n}")
    room_type = ChatRoom.RoomType.DM
    created_by = factory.LazyFunction(uuid.uuid4)

    @factory.post_generation
    def participants(self, create, extracted, **kwargs):
        if not create:
            return
        for uid in extracted or [uuid.uuid4(), uuid.uuid4()]:
            ChatRoomParticipant.objects.create(room=self, user_id=uid)
