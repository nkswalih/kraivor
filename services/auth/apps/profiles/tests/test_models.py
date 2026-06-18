import pytest
from django.db import IntegrityError

from profiles.models import Profile, UserFollow
from profiles.tests.factories import FollowFactory, ProfileFactory, UserFactory


@pytest.mark.django_db
class TestProfileModel:
    def test_create_profile(self, user):
        profile = ProfileFactory(user=user)
        assert profile.username
        assert profile.display_name
        assert profile.reputation_score == 0
        assert profile.followers_count == 0
        assert profile.following_count == 0

    def test_unique_username(self):
        p1 = ProfileFactory(username="unique")
        with pytest.raises(IntegrityError):
            ProfileFactory(username="unique")

    def test_one_to_one_user(self, user):
        profile = ProfileFactory(user=user)
        with pytest.raises(IntegrityError):
            ProfileFactory(user=user)

    def test_soft_delete(self, user):
        profile = ProfileFactory(user=user)
        assert not profile.is_deleted
        profile.soft_delete()
        profile.refresh_from_db()
        assert profile.is_deleted
        assert profile.deleted_at is not None

    def test_active_manager_excludes_deleted(self, user):
        profile = ProfileFactory(user=user)
        profile.soft_delete()
        assert Profile.objects.filter(username=profile.username).count() == 0

    def test_str(self, user):
        profile = ProfileFactory(user=user, username="testuser")
        assert str(profile) == "Profile(testuser)"


@pytest.mark.django_db
class TestUserFollowModel:
    def test_create_follow(self):
        follow = FollowFactory()
        assert follow.follower is not None
        assert follow.following is not None

    def test_unique_follow(self):
        follow = FollowFactory()
        with pytest.raises(IntegrityError):
            UserFollow.objects.create(
                follower=follow.follower, following=follow.following
            )

    def test_self_follow_allowed_by_model(self, user):
        UserFollow.objects.create(follower=user, following=user)

    def test_str(self):
        follow = FollowFactory()
        assert str(follow).startswith("UserFollow(")
