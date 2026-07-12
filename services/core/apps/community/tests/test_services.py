import pytest
import uuid

from ..models import Comment, Discussion
from ..services import CommentService, DiscussionService, TagService, VoteService
from .factories import CommentFactory, DiscussionFactory, TagFactory, VoteFactory


@pytest.mark.django_db
class TestDiscussionService:
    def test_create_discussion(self, user_id):
        d = DiscussionService.create_discussion(
            {
                "title": "Test Discussion Title Here",
                "body": "This is the body of the test discussion.",
            },
            user_id=user_id,
            username="testuser",
            display_name="Test User",
            avatar_url="",
        )
        assert d.title == "Test Discussion Title Here"
        assert d.author_username == "testuser"

    def test_create_with_tags(self, user_id, tag):
        d = DiscussionService.create_discussion(
            {
                "title": "Test Discussion Title Here",
                "body": "This is the body of the test discussion.",
                "tags": [tag.name],
            },
            user_id=user_id,
            username="testuser",
            display_name="Test User",
            avatar_url="",
        )
        assert list(d.tags.all())

    def test_list_discussions(self, user_id):
        DiscussionFactory.create_batch(3, author_id=uuid.UUID(user_id))
        items, total = DiscussionService.list_discussions(page=1)
        assert total >= 3
        assert len(items) >= 3

    def test_get_detail(self, user_id):
        d = DiscussionFactory(author_id=uuid.UUID(user_id))
        result = DiscussionService.get_detail(str(d.id))
        assert result.id == d.id

    def test_soft_delete(self, user_id):
        d = DiscussionFactory(author_id=uuid.UUID(user_id))
        DiscussionService.soft_delete(d, user_id)
        assert Discussion.all_objects.filter(id=d.id, deleted_at__isnull=False).exists()

    def test_get_trending(self, user_id):
        DiscussionFactory.create_batch(3, author_id=uuid.UUID(user_id))
        trending = DiscussionService.get_trending(limit=10)
        assert len(trending) >= 3


@pytest.mark.django_db
class TestCommentService:
    def test_create_comment(self, user_id, discussion):
        c = CommentService.create_comment(
            discussion,
            {"body": "Great post!"},
            user_id=user_id,
            username="testuser",
            display_name="Test User",
            avatar_url="",
        )
        assert c.body == "Great post!"
        assert c.discussion == discussion

    def test_get_comments(self, user_id, discussion):
        CommentFactory.create_batch(3, discussion=discussion)
        items, total = CommentService.get_comments(str(discussion.id))
        assert total == 3

    def test_soft_delete(self, user_id, discussion):
        c = CommentFactory(discussion=discussion)
        CommentService.soft_delete(c, user_id)
        assert Comment.all_objects.filter(id=c.id, deleted_at__isnull=False).exists()


@pytest.mark.django_db
class TestVoteService:
    def test_vote_discussion_create(self, user_id, discussion):
        vote, action = VoteService.vote_discussion(discussion, user_id, 1)
        assert action == "created"
        assert vote.value == 1
        discussion.refresh_from_db()
        assert discussion.upvote_count == 1

    def test_vote_discussion_change(self, user_id, discussion):
        VoteService.vote_discussion(discussion, user_id, 1)
        vote, action = VoteService.vote_discussion(discussion, user_id, -1)
        assert action == "changed"
        assert vote.value == -1
        discussion.refresh_from_db()
        assert discussion.upvote_count == 0
        assert discussion.downvote_count == 1

    def test_remove_discussion_vote(self, user_id, discussion):
        VoteFactory(discussion=discussion, user_id=uuid.UUID(user_id))
        result = VoteService.remove_discussion_vote(discussion, user_id)
        assert result is True


@pytest.mark.django_db
class TestTagService:
    def test_get_popular_tags(self):
        TagFactory.create_batch(3)
        tags = TagService.get_popular_tags(limit=10)
        assert len(tags) == 3

    def test_search_tags(self):
        TagFactory(name="python")
        TagFactory(name="javascript")
        results = TagService.search_tags("py")
        assert len(results) == 1
        assert results[0].name == "python"
