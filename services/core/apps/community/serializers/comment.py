from rest_framework import serializers

from ..models import Comment


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
        user_votes = getattr(obj, "_user_votes", None)
        if user_votes is not None:
            return user_votes[0].value if user_votes else None
        request = self.context.get("request")
        if not request or not request.user_id:
            return None
        try:
            vote = obj.votes.filter(user_id=request.user_id).first()
            return vote.value if vote else None
        except Exception:
            return None

    def get_reply_count(self, obj) -> int:
        all_replies = getattr(obj, "_all_replies", None)
        if all_replies is not None:
            return len(all_replies)
        return obj.replies.count()


class CreateCommentSerializer(serializers.Serializer):
    body = serializers.CharField(min_length=1, max_length=5000)
    parent_id = serializers.UUIDField(required=False, allow_null=True)
