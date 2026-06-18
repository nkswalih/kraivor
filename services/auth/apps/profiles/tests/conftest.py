import pytest
from rest_framework.test import APIClient

from profiles.tests.factories import ProfileFactory, UserFactory


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def profile(user):
    return ProfileFactory(user=user)


@pytest.fixture
def other_user():
    return UserFactory()


@pytest.fixture
def other_profile(other_user):
    return ProfileFactory(user=other_user)
