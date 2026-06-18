import uuid

from django.conf import settings
from django.db import models


class ActiveProfileManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class PublicProfileManager(ActiveProfileManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_public=True)


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    username = models.CharField(max_length=50, unique=True, db_index=True)
    display_name = models.CharField(max_length=120)
    bio = models.TextField(blank=True, default="", max_length=1000)
    avatar_url = models.URLField(blank=True, default="")
    banner_url = models.URLField(blank=True, default="")
    website_url = models.URLField(blank=True, default="")
    github_username = models.CharField(max_length=100, blank=True, default="")
    twitter_username = models.CharField(max_length=100, blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    location = models.CharField(max_length=150, blank=True, default="")
    is_public = models.BooleanField(default=True, db_index=True)
    reputation_score = models.IntegerField(default=0, db_index=True)
    followers_count = models.IntegerField(default=0)
    following_count = models.IntegerField(default=0)
    discussion_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveProfileManager()
    public = PublicProfileManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "profiles"
        indexes = [
            models.Index(fields=["username"], name="profile_username_idx"),
            models.Index(
                fields=["-reputation_score"], name="profile_reputation_idx"
            ),
            models.Index(
                fields=["is_public", "-reputation_score"],
                name="profile_public_reputation_idx",
            ),
        ]

    def __str__(self):
        return f"Profile({self.username})"

    def soft_delete(self):
        self.deleted_at = models.functions.Now()
        self.save(update_fields=["deleted_at", "updated_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class UserFollow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="following_relationships",
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="follower_relationships",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_follows"
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "following"],
                name="unique_user_follow",
            )
        ]
        indexes = [
            models.Index(
                fields=["follower_id", "-created_at"],
                name="follow_follower_idx",
            ),
            models.Index(
                fields=["following_id", "-created_at"],
                name="follow_following_idx",
            ),
        ]

    def __str__(self):
        return f"UserFollow({self.follower_id}→{self.following_id})"
