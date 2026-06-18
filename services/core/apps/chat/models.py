import uuid

from django.db import models


class ChatRoom(models.Model):
    class RoomType(models.TextChoices):
        WORKSPACE = "workspace", "Workspace General"
        GROUP = "group", "Group Chat"
        AI = "ai", "AI Thread"
        DM = "dm", "Direct Message"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="chat_rooms"
    )
    name = models.CharField(max_length=255)
    room_type = models.CharField(max_length=20, choices=RoomType.choices)
    topic = models.TextField(blank=True, default="")
    created_by = models.UUIDField()
    is_active = models.BooleanField(default=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "chat"
        db_table = "chat_rooms"
        verbose_name = "Chat Room"
        verbose_name_plural = "Chat Rooms"
        indexes = [
            models.Index(fields=["workspace", "room_type"]),
            models.Index(fields=["workspace", "created_by"]),
            models.Index(fields=["is_active", "-last_message_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.room_type})"
