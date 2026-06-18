import pytest
from profiles.serializers import (
    FollowerSerializer,
    FollowingSerializer,
    FollowSerializer,
    ProfileSerializer,
    UpdateProfileSerializer,
)
from profiles.tests.factories import FollowFactory, ProfileFactory


@pytest.mark.django_db
class TestProfileSerializer:
    def test_serialize(self, profile):
        serializer = ProfileSerializer(profile)
        assert serializer.data["username"] == profile.username
        assert "reputation_score" in serializer.data

    def test_serialize_many(self):
        profiles = ProfileFactory.create_batch(3)
        serializer = ProfileSerializer(profiles, many=True)
        assert len(serializer.data) == 3


@pytest.mark.django_db
class TestUpdateProfileSerializer:
    def test_validate_username_valid(self, profile):
        serializer = UpdateProfileSerializer(profile, data={"username": "new_valid_name"}, partial=True)
        assert serializer.is_valid()

    def test_validate_username_empty(self, profile):
        serializer = UpdateProfileSerializer(profile, data={"username": ""}, partial=True)
        assert not serializer.is_valid()

    def test_validate_username_sanitized(self, profile):
        serializer = UpdateProfileSerializer(profile, data={"username": "  UPPER_CASE  "}, partial=True)
        assert serializer.is_valid()
        serializer.save()
        profile.refresh_from_db()
        assert profile.username == "upper_case"

    def test_validate_username_too_short(self, profile):
        serializer = UpdateProfileSerializer(profile, data={"username": "a#b"}, partial=True)
        assert serializer.is_valid()
        serializer.save()
        assert profile.username == "ab"


@pytest.mark.django_db
class TestFollowSerializer:
    def test_serialize(self):
        follow = FollowFactory()
        serializer = FollowSerializer(follow)
        assert "id" in serializer.data
        assert "follower" in serializer.data


@pytest.mark.django_db
class TestFollowerSerializer:
    def test_serialize(self, user, other_user):
        follow = FollowFactory(follower=other_user, following=user)
        serializer = FollowerSerializer(follow)
        assert "username" in serializer.data
        assert "followed_at" in serializer.data


@pytest.mark.django_db
class TestFollowingSerializer:
    def test_serialize(self, user, other_user):
        follow = FollowFactory(follower=user, following=other_user)
        serializer = FollowingSerializer(follow)
        assert "username" in serializer.data
        assert "followed_at" in serializer.data
