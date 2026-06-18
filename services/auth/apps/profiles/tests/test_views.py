
import pytest
from django.urls import reverse
from profiles.models import UserFollow
from rest_framework import status


@pytest.mark.django_db
class TestProfileDetailView:
    def test_get_public_profile(self, client, profile):
        url = reverse("profile-detail", kwargs={"username": profile.username})
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["username"] == profile.username
        assert data["is_following"] is False
        assert data["is_owner"] is False

    def test_get_own_profile(self, client, profile, user):
        client.force_authenticate(user=user)
        url = reverse("profile-detail", kwargs={"username": profile.username})
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["is_owner"] is True

    def test_get_nonexistent(self, client):
        url = reverse("profile-detail", kwargs={"username": "nobody"})
        resp = client.get(url)
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_update_own_profile(self, client, profile, user):
        client.force_authenticate(user=user)
        url = reverse("profile-detail", kwargs={"username": profile.username})
        resp = client.patch(
            url,
            {"display_name": "New Name"},
            content_type="application/json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["display_name"] == "New Name"

    def test_update_other_profile_forbidden(self, client, profile, user, other_user, other_profile):
        client.force_authenticate(user=user)
        url = reverse("profile-detail", kwargs={"username": other_profile.username})
        resp = client.patch(
            url,
            {"display_name": "Hacked Name"},
            content_type="application/json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestMyProfileView:
    def test_get_my_profile(self, client, profile, user):
        client.force_authenticate(user=user)
        url = reverse("my-profile")
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["username"] == profile.username

    def test_get_my_profile_no_auth(self, client):
        url = reverse("my-profile")
        resp = client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestProfileSearchView:
    def test_search(self, client, profile):
        url = reverse("profile-search")
        resp = client.get(url, {"q": profile.username[:3]})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 1

    def test_search_empty_query(self, client):
        url = reverse("profile-search")
        resp = client.get(url, {"q": ""})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestFollowView:
    def test_follow(self, client, user, other_user, other_profile):
        client.force_authenticate(user=user)
        url = reverse("profile-follow", kwargs={"username": other_profile.username})
        resp = client.post(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert UserFollow.objects.filter(follower=user, following=other_user).exists()

    def test_follow_self(self, client, user, profile):
        client.force_authenticate(user=user)
        url = reverse("profile-follow", kwargs={"username": profile.username})
        resp = client.post(url)
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_unfollow(self, client, user, other_user, other_profile):
        client.force_authenticate(user=user)
        UserFollow.objects.create(follower=user, following=other_user)
        url = reverse("profile-follow", kwargs={"username": other_profile.username})
        resp = client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not UserFollow.objects.filter(follower=user, following=other_user).exists()

    def test_follow_no_auth(self, client, other_profile):
        url = reverse("profile-follow", kwargs={"username": other_profile.username})
        resp = client.post(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestLeaderboardView:
    def test_leaderboard(self, client, profile):
        url = reverse("profile-leaderboard")
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert "results" in resp.json()


@pytest.mark.django_db
class TestTopContributorsView:
    def test_top_contributors(self, client, profile):
        url = reverse("top-contributors")
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert "results" in resp.json()
