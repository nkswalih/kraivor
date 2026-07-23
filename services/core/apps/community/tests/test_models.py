import pytest
import uuid
from django.db import IntegrityError

from ..models import Discussion
from .factories import CommentFactory, DiscussionFactory, TagFactory, VoteFactory


@pytest.mark.django_db
class TestTagModel:
    def test_create_tag(self):
        tag = TagFactory()
        assert tag.name
        assert tag.slug
        assert tag.usage_count == 0

    def test_unique_name(self):
        TagFactory(name="unique")
        with pytest.raises(IntegrityError):
            TagFactory(name="unique")

    def test_str(self):
        tag = TagFactory(name="python")
        assert str(tag) == "Tag(python)"


@pytest.mark.django_db
class TestDiscussionModel:
    def test_create_discussion(self, user_id):
        d = DiscussionFactory(author_id=uuid.UUID(user_id))
        assert d.title
        assert d.upvote_count == 0
        assert d.comment_count == 0

    def test_soft_delete(self, user_id):
        d = DiscussionFactory(author_id=uuid.UUID(user_id))
        d.soft_delete()
        d.refresh_from_db()
        assert d.deleted_at is not None

    def test_active_manager_excludes_deleted(self, user_id):
        d = DiscussionFactory(author_id=uuid.UUID(user_id))
        d.soft_delete()
        assert Discussion.objects.filter(id=d.id).count() == 0

    def test_tags_relation(self, user_id):
        d = DiscussionFactory(author_id=uuid.UUID(user_id))
        tag = TagFactory()
        d.tags.add(tag)
        assert list(d.tags.all()) == [tag]

    def test_str(self, user_id):
        d = DiscussionFactory(author_id=uuid.UUID(user_id), title="My Discussion Title")
        assert "My Discussion Title" in str(d)


@pytest.mark.django_db
class TestCommentModel:
    def test_create_comment(self, discussion):
        c = CommentFactory(discussion=discussion)
        assert c.body
        assert c.upvote_count == 0

    def test_soft_delete(self, discussion):
        c = CommentFactory(discussion=discussion)
        c.soft_delete()
        c.refresh_from_db()
        assert c.deleted_at is not None

    def test_parent_relation(self, discussion):
        parent = CommentFactory(discussion=discussion)
        child = CommentFactory(discussion=discussion, parent=parent)
        assert child.parent == parent
        assert list(parent.replies.all()) == [child]


@pytest.mark.django_db
class TestVoteModel:
    def test_create_discussion_vote(self, discussion, user_id):
        v = VoteFactory(discussion=discussion, user_id=uuid.UUID(user_id))
        assert v.value in (1, -1)
        assert v.discussion == discussion

    def test_unique_discussion_vote(self, discussion, user_id):
        VoteFactory(discussion=discussion, user_id=uuid.UUID(user_id))
        with pytest.raises(IntegrityError):
            VoteFactory(discussion=discussion, user_id=uuid.UUID(user_id))
