import uuid
from django.db import models

from apps.workspaces.models import TimestampedModel

# ─── V2 Models ─────────────────────────────────────────────────────────────────
# These live alongside the legacy models until Phase 4 (full deprecation).


class Room(TimestampedModel):
    """Chat v2 room — user-centric topology. DM, Group, Workspace Team, or AI Chat."""

    class RoomType(models.TextChoices):
        DM = "DM", "Direct Message"
        GROUP = "GROUP", "Group Chat"
        WORKSPACE_TEAM = "WORKSPACE_TEAM", "Workspace Team"
        AI_CHAT = "AI_CHAT", "AI Chat"

    name = models.CharField(max_length=255)
    room_type = models.CharField(max_length=20, choices=RoomType.choices, db_index=True)
    is_public = models.BooleanField(default=False)

    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_group",
        help_text="Only set for WORKSPACE_TEAM — all other types are workspace-agnostic.",
    )
    created_by = models.UUIDField()

    member_count = models.IntegerField(default=1)
    message_count = models.IntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_content = models.TextField(blank=True, default="")
    last_message_sender_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        app_label = "chat"
        db_table = "chat_v2_rooms"
        verbose_name = "Chat V2 Room"
        verbose_name_plural = "Chat V2 Rooms"
        indexes = [
            models.Index(
                fields=["room_type", "-last_message_at"], name="idx_v2_room_type_recent"
            ),
            models.Index(fields=["workspace"], name="idx_v2_room_workspace"),
            models.Index(fields=["created_by"], name="idx_v2_room_creator"),
            models.Index(
                fields=["is_public", "room_type"], name="idx_v2_room_public_type"
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.room_type})"


class RoomMember(TimestampedModel):
    """V2 membership — tracks last read seq for unread counting."""

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="v2_members")
    user_id = models.UUIDField()
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_seq = models.BigIntegerField(default=0)

    class Meta:
        app_label = "chat"
        db_table = "chat_v2_room_members"
        verbose_name = "Chat V2 Room Member"
        verbose_name_plural = "Chat V2 Room Members"
        constraints = [
            models.UniqueConstraint(
                fields=["room", "user_id"], name="uq_v2_room_member"
            )
        ]
        indexes = [
            models.Index(fields=["user_id", "room"], name="idx_v2_member_user_room"),
            models.Index(
                fields=["user_id", "-joined_at"], name="idx_v2_member_user_recent"
            ),
        ]

    def __str__(self):
        return f"V2Member({self.user_id}) in {self.room_id}"


class Role(TimestampedModel):
    """Custom role with granular boolean permissions per room."""

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="v2_roles")
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default="#9898a6")
    priority = models.PositiveSmallIntegerField(default=0)

    can_delete_messages = models.BooleanField(default=False)
    can_pin_messages = models.BooleanField(default=False)
    can_manage_members = models.BooleanField(default=False)
    can_manage_roles = models.BooleanField(default=False)
    can_share_repositories = models.BooleanField(default=False)
    can_view_audit_logs = models.BooleanField(default=False)

    class Meta:
        app_label = "chat"
        db_table = "chat_v2_roles"
        verbose_name = "Chat V2 Role"
        verbose_name_plural = "Chat V2 Roles"
        indexes = [
            models.Index(fields=["room", "priority"], name="idx_v2_role_room_priority")
        ]

    def __str__(self):
        return f"{self.name} @ {self.room_id}"


class RoomMemberRole(TimestampedModel):
    """Junction: members can hold multiple roles."""

    member = models.ForeignKey(
        RoomMember, on_delete=models.CASCADE, related_name="v2_roles"
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        app_label = "chat"
        db_table = "chat_v2_member_roles"
        verbose_name = "Chat V2 Member Role"
        verbose_name_plural = "Chat V2 Member Roles"
        constraints = [
            models.UniqueConstraint(fields=["member", "role"], name="uq_v2_member_role")
        ]

    def __str__(self):
        return f"V2MemberRole({self.member_id} → {self.role_id})"


class PinnedMessage(TimestampedModel):
    """Pinned message within a room."""

    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="v2_pinned_messages"
    )
    message_seq = models.BigIntegerField()
    pinned_by = models.UUIDField()
    pinned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "chat"
        db_table = "chat_v2_pinned_messages"
        verbose_name = "Chat V2 Pinned Message"
        verbose_name_plural = "Chat V2 Pinned Messages"
        indexes = [
            models.Index(
                fields=["room", "-pinned_at"], name="idx_v2_pinned_room_recent"
            )
        ]

    def __str__(self):
        return f"Pinned #{self.message_seq} in {self.room_id}"


class Draft(TimestampedModel):
    """Saved draft per user per room."""

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="v2_drafts")
    user_id = models.UUIDField()
    content = models.TextField(blank=True, default="")
    reply_to_seq = models.BigIntegerField(null=True, blank=True)
    attachment_urls = models.JSONField(default=list, blank=True)

    class Meta:
        app_label = "chat"
        db_table = "chat_v2_drafts"
        verbose_name = "Chat V2 Draft"
        verbose_name_plural = "Chat V2 Drafts"
        indexes = [
            models.Index(fields=["room", "user_id"], name="idx_v2_draft_room_user")
        ]

    def __str__(self):
        return f"Draft({self.user_id} @ {self.room_id})"


class RoomInvite(TimestampedModel):
    """Invitation to a group room."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="v2_invites")
    target_user_id = models.UUIDField()
    invited_by_id = models.UUIDField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "chat"
        db_table = "chat_v2_room_invites"
        verbose_name = "Chat V2 Room Invite"
        verbose_name_plural = "Chat V2 Room Invites"
        indexes = [
            models.Index(
                fields=["target_user_id", "status"], name="idx_v2_invite_user_status"
            )
        ]

    def __str__(self):
        return f"Invite({self.target_user_id} → {self.room_id}: {self.status})"


class ScheduledMessage(TimestampedModel):
    """Message scheduled for future delivery."""

    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="v2_scheduled_messages"
    )
    sender_id = models.UUIDField()
    content = models.TextField()
    send_at = models.DateTimeField(db_index=True)
    is_sent = models.BooleanField(default=False, db_index=True)

    class Meta:
        app_label = "chat"
        db_table = "chat_v2_scheduled_messages"
        verbose_name = "Chat V2 Scheduled Message"
        verbose_name_plural = "Chat V2 Scheduled Messages"
        indexes = [
            models.Index(fields=["send_at", "is_sent"], name="idx_v2_scheduled_pending")
        ]

    def __str__(self):
        return f"Scheduled({self.sender_id} @ {self.send_at})"


# ─── Legacy Models (Deprecated — keep until Phase 4) ──────────────────────────


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
        indexes = [models.Index(fields=["user_id", "room"])]

    def __str__(self):
        return f"Participant({self.user_id}) in {self.room_id}"
