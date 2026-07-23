"""
Notification and FCM token data models.

Notification stores per-user notifications with type classification,
read tracking, and expiry support. FCMToken maps user device tokens
for Firebase Cloud Messaging push delivery.
"""

import uuid
from django.db import models


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        WORKSPACE_INVITATION = "workspace.invitation", "Workspace Invitation"
        MEMBER_JOINED = "workspace.member.joined", "Member Joined"
        MEMBER_REMOVED = "workspace.member.removed", "Member Removed"
        MEMBER_ROLE_CHANGED = "workspace.member.role_changed", "Role Changed"
        ANALYSIS_COMPLETED = "analysis.completed", "Analysis Completed"
        ANALYSIS_FAILED = "analysis.failed", "Analysis Failed"
        AI_INDEX_COMPLETED = "ai.index.completed", "AI Index Completed"
        AI_ANALYSIS_COMPLETED = "ai.analysis.completed", "AI Analysis Completed"
        CHAT_MESSAGE = "chat.message", "New Chat Message"
        CHAT_MENTION = "chat.mention", "Chat Mention"
        FOLLOW_NEW = "profile.follow.new", "New Follower"
        DISCUSSION_CREATED = "community.discussion.created", "Discussion Created"
        COMMENT_CREATED = "community.comment.created", "Comment Created"
        COMMENT_REPLY = "community.comment.reply", "Comment Reply"
        DISCUSSION_UPVOTED = "community.discussion.upvoted", "Discussion Upvoted"
        COMMENT_UPVOTED = "community.comment.upvoted", "Comment Upvoted"
        PROJECT_CREATED = "project.created", "Project Created"
        TASK_CREATED = "task.created", "Task Created"
        TASK_ASSIGNED = "task.assigned", "Task Assigned"
        TASK_COMPLETED = "task.completed", "Task Completed"
        TASK_BLOCKED = "task.blocked", "Task Blocked"
        TASK_OVERDUE = "task.overdue", "Task Overdue"
        REPOSITORY_CONNECTED = "repository.connected", "Repository Connected"
        REPOSITORY_DISCONNECTED = "repository.disconnected", "Repository Disconnected"
        SYSTEM = "system", "System Notification"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=50, choices=NotificationType.choices
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    link = models.URLField(max_length=500, blank=True, default="")
    metadata = models.JSONField(null=True, blank=True, default=dict)
    actor_id = models.UUIDField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "notifications"
        db_table = "notifications"
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["user_id", "-created_at"]),
            models.Index(fields=["user_id", "read_at"]),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None


class FCMToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True)
    token = models.TextField()
    platform = models.CharField(
        max_length=20, choices=[("ios", "iOS"), ("android", "Android"), ("web", "Web")]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "notifications"
        db_table = "fcm_tokens"
        verbose_name = "FCM Token"
        verbose_name_plural = "FCM Tokens"
        unique_together = [("user_id", "token")]

    def __str__(self):
        return f"{self.user_id} ({self.platform})"
