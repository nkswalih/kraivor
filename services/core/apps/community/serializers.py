from rest_framework import serializers

from .models import Comment, Discussion, Tag, Vote


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "description", "usage_count", "created_at"]
        read_only_fields = ["id", "usage_count", "created_at"]


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
        request = self.context.get("request")
        if not request or not request.user_id:
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


class CommentSerializer(serializers.ModelSerializer):
    user_vote = serializers.SerializerMethodField()
    reply_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "discussion_id",
            "parent_id",
            "body",
            "author_id",
            "author_username",
            "author_display_name",
            "author_avatar_url",
            "upvote_count",
            "downvote_count",
            "user_vote",
            "reply_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "author_id",
            "author_username",
            "author_display_name",
            "author_avatar_url",
            "upvote_count",
            "downvote_count",
            "user_vote",
            "reply_count",
            "created_at",
            "updated_at",
        ]

    def get_user_vote(self, obj) -> int | None:
        request = self.context.get("request")
        if not request or not request.user_id:
            return None
        try:
            vote = obj.votes.filter(user_id=request.user_id).first()
            return vote.value if vote else None
        except Exception:
            return None

    def get_reply_count(self, obj) -> int:
        return obj.replies.count()


class CreateCommentSerializer(serializers.Serializer):
    body = serializers.CharField(min_length=1, max_length=5000)
    parent_id = serializers.UUIDField(required=False, allow_null=True)


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ["id", "user_id", "discussion_id", "comment_id", "value", "created_at"]
        read_only_fields = ["id", "user_id", "created_at"]
