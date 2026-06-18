import re

from profiles.models import Profile, UserFollow
from rest_framework import serializers


class ProfileSerializer(serializers.ModelSerializer):
    user_avatar_url = serializers.URLField(source="user.avatar_url", read_only=True, allow_null=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "username",
            "display_name",
            "bio",
            "avatar_url",
            "user_avatar_url",
            "banner_url",
            "website_url",
            "github_username",
            "twitter_username",
            "linkedin_url",
            "location",
            "is_public",
            "reputation_score",
            "followers_count",
            "following_count",
            "discussion_count",
            "comment_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reputation_score",
            "followers_count",
            "following_count",
            "discussion_count",
            "comment_count",
            "created_at",
            "updated_at",
        ]


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "username",
            "display_name",
            "bio",
            "avatar_url",
            "banner_url",
            "website_url",
            "github_username",
            "twitter_username",
            "linkedin_url",
            "location",
            "is_public",
        ]

    def validate_username(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Username is required.")
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9_]", "", value)
        value = re.sub(r"_+", "_", value).strip("_")
        if not value:  # pragma: no cover
            raise serializers.ValidationError("Username must contain at least one letter.")
        existing = Profile.objects.filter(username=value).exclude(id=self.instance.id).first()
        if existing:
            raise serializers.ValidationError("This username is not available.")
        return value


class FollowSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFollow
        fields = ["id", "follower", "following", "created_at"]
        read_only_fields = ["id", "follower", "created_at"]


class FollowerSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="follower.id")
    username = serializers.CharField(source="follower.profile.username")
    display_name = serializers.CharField(source="follower.profile.display_name")
    avatar_url = serializers.URLField(source="follower.profile.avatar_url")
    user_avatar_url = serializers.URLField(source="follower.avatar_url", allow_null=True)
    bio = serializers.CharField(source="follower.profile.bio")
    followed_at = serializers.DateTimeField(source="created_at")


class FollowingSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="following.id")
    username = serializers.CharField(source="following.profile.username")
    display_name = serializers.CharField(source="following.profile.display_name")
    avatar_url = serializers.URLField(source="following.profile.avatar_url")
    user_avatar_url = serializers.URLField(source="following.avatar_url", allow_null=True)
    bio = serializers.CharField(source="following.profile.bio")
    followed_at = serializers.DateTimeField(source="created_at")
