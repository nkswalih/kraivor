import pytest
import uuid
from django.urls import reverse
from rest_framework import status

from .factories import (
    DiscussionFactory,
    TagFactory,
    VoteFactory,
)


@pytest.mark.django_db
class TestDiscussionListView:
    def test_list_discussions(self, client, user_id, discussion):
        url = reverse("discussion-list")
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["total"] >= 1

    def test_create_discussion(self, client, user_id):
        url = reverse("discussion-list")
        resp = client.post(
            url,
            {
                "title": "Test Discussion Title Here",
                "body": "This is the body of the test discussion.",
                "author_username": "testuser",
                "author_display_name": "Test User",
            },
            content_type="application/json",
            HTTP_X_USER_ID=str(user_id),
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_create_discussion_no_auth(self, client):
        url = reverse("discussion-list")
        resp = client.post(
            url,
            {"title": "Test", "body": "Body"},
            content_type="application/json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDiscussionDetailView:
    def test_get(self, client, discussion):
        url = reverse("discussion-detail", kwargs={"discussion_id": discussion.id})
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK

    def test_delete_own(self, client, user_id, discussion):
        url = reverse("discussion-detail", kwargs={"discussion_id": discussion.id})
        resp = client.delete(url, HTTP_X_USER_ID=str(discussion.author_id))
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_other_forbidden(self, client, user_id, discussion):
        url = reverse("discussion-detail", kwargs={"discussion_id": discussion.id})
        resp = client.delete(url, HTTP_X_USER_ID=str(uuid.uuid4()))
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDiscussionVoteView:
    def test_upvote(self, client, user_id, discussion):
        url = reverse("discussion-vote", kwargs={"discussion_id": discussion.id})
        resp = client.post(
            url,
            {"value": 1},
            content_type="application/json",
            HTTP_X_USER_ID=str(user_id),
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["value"] == 1

    def test_remove_vote(self, client, user_id, discussion):
        VoteFactory(discussion=discussion, user_id=uuid.UUID(user_id))
        url = reverse("discussion-vote", kwargs={"discussion_id": discussion.id})
        resp = client.delete(url, HTTP_X_USER_ID=str(user_id))
        assert resp.status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.django_db
class TestTrendingDiscussionsView:
    def test_trending(self, client, user_id):
        DiscussionFactory.create_batch(3, author_id=uuid.UUID(user_id))
        url = reverse("discussion-trending")
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()["results"]) >= 3


@pytest.mark.django_db
class TestPopularTagsView:
    def test_popular_tags(self, client):
        TagFactory.create_batch(3)
        url = reverse("tags-popular")
        resp = client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.json()["results"]) == 3
