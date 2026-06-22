import pytest
import uuid
from rest_framework.test import APIRequestFactory

from .factories import DiscussionFactory, TagFactory


@pytest.fixture
def api_factory():
    return APIRequestFactory()


@pytest.fixture
def user_id():
    return str(uuid.uuid4())


@pytest.fixture
def tag():
    return TagFactory()


@pytest.fixture
def discussion(user_id):
    return DiscussionFactory(author_id=uuid.UUID(user_id))


def make_request(method, path, user_id=None, data=None):
    factory = APIRequestFactory()
    request = getattr(factory, method)(path, data or {}, format="json")
    request.user_id = user_id or str(uuid.uuid4())
    return request
