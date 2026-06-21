from rest_framework import serializers

from ..models import Discussion
from .tag import TagSerializer


class DiscussionListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    user_vote = serializers.SerializerMethodField()

    class Meta:
        model = Discussion
        fields = [
            "id",
            "workspace_id",
            "title",
            "body",
            "author_id",
            "author_username",
            "author_display_name",
            "author_avatar_url",
            "upvote_count",
            "downvote_count",
            "comment_count",
            "tags",
            "is_pinned",
            "is_locked",
            "is_resolved",
            "user_vote",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_user_vote(self, obj) -> int | None:
        user_votes = getattr(obj, "_user_votes", None)
        if user_votes is not None:
            return user_votes[0].value if user_votes else None
        request = self.context.get("request")
        if not request or not getattr(request, "user_id", None):
            return None
        try:
            vote = obj.votes.filter(user_id=request.user_id).first()
            return vote.value if vote else None
        except Exception:
            return None


class DiscussionDetailSerializer(DiscussionListSerializer):
    class Meta(DiscussionListSerializer.Meta):
        fields = DiscussionListSerializer.Meta.fields + ["body"]


class CreateDiscussionSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=10, max_length=200)
    body = serializers.CharField(min_length=20, max_length=20000)
    workspace_id = serializers.UUIDField(required=False, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
    )


class UpdateDiscussionSerializer(serializers.Serializer):
    title = serializers.CharField(min_length=10, max_length=200, required=False)
    body = serializers.CharField(min_length=20, max_length=20000, required=False)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
    )
    is_resolved = serializers.BooleanField(required=False)
