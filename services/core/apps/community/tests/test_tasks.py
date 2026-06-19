import uuid

import pytest

from ..models import Discussion
from ..tasks import recalculate_discussion_counters, update_author_denormalization
from .factories import DiscussionFactory


@pytest.mark.django_db
class TestCommunityTasks:
    def test_update_author_denormalization(self):
        author_id = uuid.uuid4()
        d1 = DiscussionFactory(author_id=author_id)
        d2 = DiscussionFactory(author_id=author_id)
        update_author_denormalization(
            str(author_id), "newuser", "New User", "https://example.com/avatar.jpg"
        )
        d1.refresh_from_db()
        d2.refresh_from_db()
        assert d1.author_username == "newuser"
        assert d1.author_display_name == "New User"
        assert d2.author_username == "newuser"

    def test_recalculate_discussion_counters(self, discussion):
        recalculate_discussion_counters(str(discussion.id))
        discussion.refresh_from_db()
        assert discussion.upvote_count >= 0
