from rest_framework import serializers

from ..models import Vote


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ["id", "user_id", "discussion_id", "comment_id", "value", "created_at"]
        read_only_fields = ["id", "user_id", "created_at"]
