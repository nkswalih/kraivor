import pytest
from django.test import RequestFactory
from profiles.permissions import IsAuthenticatedOrReadOnly, IsProfileOwner
from profiles.tests.factories import ProfileFactory, UserFactory
from rest_framework.test import APIRequestFactory


@pytest.mark.django_db
class TestIsProfileOwner:
    def test_owner_allowed(self):
        user = UserFactory()
        profile = ProfileFactory(user=user)
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = user
        perm = IsProfileOwner()
        assert perm.has_object_permission(request, None, profile)

    def test_non_owner_denied(self):
        owner = UserFactory()
        other = UserFactory()
        profile = ProfileFactory(user=owner)
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = other
        perm = IsProfileOwner()
        assert not perm.has_object_permission(request, None, profile)

    def test_unauthenticated_denied(self):
        user = UserFactory()
        profile = ProfileFactory(user=user)
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = type("AnonUser", (), {"is_authenticated": False})()
        perm = IsProfileOwner()
        assert not perm.has_object_permission(request, None, profile)


@pytest.mark.django_db
class TestIsAuthenticatedOrReadOnly:
    def test_safe_method_allowed(self):
        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = type("AnonUser", (), {"is_authenticated": False})()
        perm = IsAuthenticatedOrReadOnly()
        assert perm.has_permission(request, None)

    def test_unsafe_method_denied_unauthenticated(self):
        factory = APIRequestFactory()
        request = factory.post("/")
        request.user = type("AnonUser", (), {"is_authenticated": False})()
        perm = IsAuthenticatedOrReadOnly()
        assert not perm.has_permission(request, None)

    def test_unsafe_method_allowed_authenticated(self):
        user = UserFactory()
        factory = APIRequestFactory()
        request = factory.post("/")
        request.user = user
        perm = IsAuthenticatedOrReadOnly()
        assert perm.has_permission(request, None)
