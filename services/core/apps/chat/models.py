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
    last_message_content = models.TextField(blank=True, default="")
    last_message_sender_name = models.CharField(max_length=255, blank=True, default="")
    message_count = models.IntegerField(default=0)
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


class ChatRoomParticipant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE, related_name="participants"
    )
    user_id = models.UUIDField()
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    last_read_message_count = models.IntegerField(default=0)

    class Meta:
        app_label = "chat"
        db_table = "chat_room_participants"
        verbose_name = "Chat Room Participant"
        verbose_name_plural = "Chat Room Participants"
        unique_together = [["room", "user_id"]]
        indexes = [
            models.Index(fields=["user_id", "room"]),
        ]

    def __str__(self):
        return f"Participant({self.user_id}) in {self.room_id}"
