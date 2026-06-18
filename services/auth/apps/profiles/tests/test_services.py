import pytest

from profiles.models import UserFollow
from profiles.services import ProfileService, ReputationService
from profiles.tests.factories import FollowFactory, ProfileFactory, UserFactory


@pytest.mark.django_db
class TestProfileService:
    def test_get_by_username(self, user, profile):
        result = ProfileService.get_by_username(profile.username)
        assert result == profile

    def test_get_by_username_not_found(self):
        assert ProfileService.get_by_username("nonexistent") is None

    def test_get_by_user_id(self, user, profile):
        result = ProfileService.get_by_user_id(str(user.id))
        assert result == profile

    def test_search_by_username(self):
        p = ProfileFactory(username="johndoe", display_name="John Doe")
        results, total = ProfileService.search("johndoe")
        assert total == 1
        assert results[0] == p

    def test_search_by_display_name(self):
        p = ProfileFactory(username="jd", display_name="Jane Doe")
        results, total = ProfileService.search("Jane")
        assert total == 1
        assert results[0] == p

    def test_search_pagination(self):
        ProfileFactory.create_batch(5)
        results, total = ProfileService.search("user", page=2, page_size=2)
        assert total >= 5
        assert len(results) <= 2

    def test_leaderboard(self):
        profiles = ProfileFactory.create_batch(3)
        results, total = ProfileService.get_leaderboard(page=1, page_size=10)
        assert total == len(profiles)

    def test_follow(self, user, other_user):
        result = ProfileService.follow(str(user.id), str(other_user.id))
        assert result is not None
        assert UserFollow.objects.filter(follower=user, following=other_user).exists()

    def test_follow_self(self, user):
        result = ProfileService.follow(str(user.id), str(user.id))
        assert result is None

    def test_follow_duplicate(self, user, other_user):
        ProfileService.follow(str(user.id), str(other_user.id))
        result = ProfileService.follow(str(user.id), str(other_user.id))
        assert result is None

    def test_unfollow(self, user, other_user):
        ProfileService.follow(str(user.id), str(other_user.id))
        result = ProfileService.unfollow(str(user.id), str(other_user.id))
        assert result is True
        assert not UserFollow.objects.filter(follower=user, following=other_user).exists()

    def test_unfollow_nonexistent(self, user, other_user):
        result = ProfileService.unfollow(str(user.id), str(other_user.id))
        assert result is False

    def test_is_following(self, user, other_user):
        ProfileService.follow(str(user.id), str(other_user.id))
        assert ProfileService.is_following(str(user.id), str(other_user.id)) is True
        assert ProfileService.is_following(str(other_user.id), str(user.id)) is False

    def test_get_followers(self, user, other_user):
        ProfileService.follow(str(other_user.id), str(user.id))
        profile = ProfileService.get_by_user_id(str(user.id))
        items, total = ProfileService.get_followers(profile)
        assert total == 1

    def test_get_following(self, user, other_user):
        ProfileService.follow(str(user.id), str(other_user.id))
        profile = ProfileService.get_by_user_id(str(user.id))
        items, total = ProfileService.get_following(profile)
        assert total == 1


@pytest.mark.django_db
class TestReputationService:
    def test_get_top_contributors(self):
        profiles = ProfileFactory.create_batch(3)
        results = ReputationService.get_top_contributors(limit=10)
        assert len(results) == len(profiles)
        assert "username" in results[0]
        assert "reputation_score" in results[0]
