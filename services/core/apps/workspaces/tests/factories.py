import uuid

import factory
import factory.django

from apps.workspaces.constants import WorkspaceRole
from apps.workspaces.models import Workspace, WorkspaceMember


class WorkspaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Workspace

    owner_id = factory.LazyFunction(lambda: uuid.uuid4())
    name = factory.Sequence(lambda n: f"Test Workspace {n}")
    slug = factory.Sequence(lambda n: f"test-workspace-{n}")


class WorkspaceMemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WorkspaceMember

    workspace = factory.SubFactory(WorkspaceFactory)
    user_id = factory.LazyFunction(lambda: uuid.uuid4())
    role = WorkspaceRole.MEMBER
