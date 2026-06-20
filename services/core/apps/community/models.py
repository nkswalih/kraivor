import uuid

from django.db import models


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, db_index=True)
    slug = models.SlugField(max_length=60, unique=True, db_index=True)
    description = models.CharField(max_length=300, blank=True, default="")
    usage_count = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "community_tags"
        ordering = ["-usage_count", "name"]

    def __str__(self):
        return f"Tag({self.name})"


class Discussion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace_id = models.UUIDField(null=True, blank=True, db_index=True)
    title = models.CharField(max_length=200)
    body = models.TextField(max_length=20000)
    # Denormalized author fields
    author_id = models.UUIDField(db_index=True)
    author_username = models.CharField(max_length=50)
    author_display_name = models.CharField(max_length=120)
    author_avatar_url = models.URLField(blank=True, default="")
    # Counters
    upvote_count = models.IntegerField(default=0, db_index=True)
    downvote_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    tags = models.ManyToManyField(Tag, related_name="discussions", blank=True)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "community_discussions"
        indexes = [
            models.Index(fields=["-created_at"], name="disc_created_idx"),
            models.Index(fields=["-upvote_count"], name="disc_upvote_idx"),
            models.Index(
                fields=["-upvote_count", "-created_at"], name="disc_trending_idx"
            ),
            models.Index(fields=["is_pinned", "-created_at"], name="disc_pinned_idx"),
        ]

    def __str__(self):
        return f"Discussion({self.title[:50]})"

    def soft_delete(self):
        self.deleted_at = models.functions.Now()
        self.save(update_fields=["deleted_at", "updated_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discussion = models.ForeignKey(
        Discussion, on_delete=models.CASCADE, related_name="comments"
    )
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    body = models.TextField(max_length=5000)
    # Denormalized author fields
    author_id = models.UUIDField(db_index=True)
    author_username = models.CharField(max_length=50)
    author_display_name = models.CharField(max_length=120)
    author_avatar_url = models.URLField(blank=True, default="")
    upvote_count = models.IntegerField(default=0)
    downvote_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "community_comments"
        indexes = [
            models.Index(fields=["discussion", "-created_at"], name="comment_disc_idx"),
            models.Index(fields=["parent", "-created_at"], name="comment_parent_idx"),
        ]

    def __str__(self):
        return f"Comment({self.id})"

    def soft_delete(self):
        self.deleted_at = models.functions.Now()
        self.save(update_fields=["deleted_at", "updated_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class Vote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    discussion = models.ForeignKey(
        Discussion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="votes",
    )
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="votes"
    )
    value = models.SmallIntegerField(choices=[(1, "Upvote"), (-1, "Downvote")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "community_votes"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(discussion__isnull=False, comment__isnull=True)
                    | models.Q(discussion__isnull=True, comment__isnull=False)
                ),
                name="vote_single_target",
            ),
            models.UniqueConstraint(
                fields=["user_id", "discussion"],
                name="unique_discussion_vote",
            ),
            models.UniqueConstraint(
                fields=["user_id", "comment"],
                name="unique_comment_vote",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "discussion"], name="vote_user_disc_idx"),
            models.Index(fields=["user_id", "comment"], name="vote_user_comment_idx"),
        ]

    def __str__(self):
        target = self.discussion_id or self.comment_id
        return f"Vote({self.value} on {target})"
