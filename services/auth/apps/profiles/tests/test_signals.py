import pytest
from profiles.models import Profile, UserFollow
from profiles.tests.factories import UserFactory


@pytest.mark.django_db
class TestCreateProfileOnRegistration:
    def test_creates_profile_on_user_creation(self):
        user = UserFactory()
        assert Profile.objects.filter(user=user).exists()

    def test_does_not_duplicate_profile(self):
        user = UserFactory()
        assert Profile.objects.filter(user=user).count() == 1


@pytest.mark.django_db
class TestFollowCounters:
    def test_increment_on_follow(self, user, other_user):
        UserFollow.objects.create(follower=user, following=other_user)
        user.profile.refresh_from_db()
        other_user.profile.refresh_from_db()
        assert user.profile.following_count == 1
        assert other_user.profile.followers_count == 1

    def test_decrement_on_unfollow(self, user, other_user):
        follow = UserFollow.objects.create(follower=user, following=other_user)
        follow.delete()
        user.profile.refresh_from_db()
        other_user.profile.refresh_from_db()
        assert user.profile.following_count == 0
        assert other_user.profile.followers_count == 0
