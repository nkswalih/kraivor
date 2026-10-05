from collections.abc import Callable

import pytest
import uuid
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from apps.chat.views.rooms import DMCreateView
from apps.workspaces.models import Workspace

from .factories import WorkspaceFactory, WorkspaceMemberFactory


@pytest.fixture
def api_factory() -> APIRequestFactory:
    return APIRequestFactory()


@pytest.fixture
def dm_view() -> Callable[..., Response]:
    return DMCreateView.as_view()


@pytest.fixture
def workspace() -> Workspace:
    """A workspace with two members, which is the case DM creation is for."""
    ws = WorkspaceFactory()
    WorkspaceMemberFactory(workspace=ws, role="owner")
    WorkspaceMemberFactory(workspace=ws)
    return ws


def post_dm(
    api_factory: APIRequestFactory,
    dm_view: Callable[..., Response],
    workspace: Workspace,
    caller: uuid.UUID,
    target: uuid.UUID,
    name: str = "target",
) -> Response:
    """Invoke the view the way the URLconf does.

    `user_id` is set on the request rather than authenticating a Django user,
    because that is what `IsChatRoomMember` reads (`getattr(request, "user_id",
    None)`) and what the view reads for `user_id_1`. `force_authenticate` would
    leave `request.user_id` unset, so every test would fail the permission for a
    reason that has nothing to do with what any of them are about.

    That assignment is the one line here mypy cannot accept: `user_id` is attached
    by middleware and is not on DRF's `Request`, so the attribute genuinely does not
    exist to the type checker. `apps/community/tests/conftest.py` has the same line,
    also unsatisfied. `setattr` would silence it and is banned by ruff B010 for
    using a literal name, so the honest error stays.
    """
    factory_request = api_factory.post(
        f"/api/workspaces/{workspace.pk}/dm/",
        {"target_user_id": str(target), "target_user_name": name},
        format="json",
    )
    factory_request.user_id = str(caller)
    return dm_view(factory_request, workspace_pk=str(workspace.pk))


@pytest.fixture
def stranger_id() -> uuid.UUID:
    """A user id with no membership anywhere."""
    return uuid.uuid4()
