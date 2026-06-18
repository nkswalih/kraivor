import pytest
from django.db.models import F

from profiles.models import Profile
from profiles.tasks import apply_reputation_event
from profiles.tests.factories import ProfileFactory


@pytest.mark.django_db
class TestReputationTask:
    def test_apply_positive_delta(self, user):
        profile = ProfileFactory(user=user)
        apply_reputation_event(str(user.id), "discussion.created", 5)
        profile.refresh_from_db()
        assert profile.reputation_score == 5

    def test_apply_negative_delta(self, user):
        profile = ProfileFactory(user=user, reputation_score=10)
        profile.save()
        apply_reputation_event(str(user.id), "discussion.deleted", -5)
        profile.refresh_from_db()
        assert profile.reputation_score == 5

    def test_unknown_profile(self):
        apply_reputation_event("00000000-0000-0000-0000-000000000000", "test", 1)
