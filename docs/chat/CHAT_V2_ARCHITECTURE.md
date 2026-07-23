# Kraivor Chat v2 — Architecture & Implementation Guide

> **Document Version:** 2.0  
> **Last Updated:** 2026-07-09  
> **Service:** Core Service — Chat Rebuild  
> **Status:** Approved — In Development  
> **Classification:** Internal — Architecture

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Topology](#2-topology)
3. [Multi-Store Architecture](#3-multi-store-architecture)
4. [PostgreSQL Data Models](#4-postgresql-data-models)
5. [DynamoDB Single-Table Design](#5-dynamodb-single-table-design)
6. [Redis State Layer](#6-redis-state-layer)
7. [S3 Asset Storage](#7-s3-asset-storage)
8. [Atomic Seq Counter](#8-atomic-seq-counter)
9. [WebSocket Protocol](#9-websocket-protocol)
10. [WebSocket Consumer](#10-websocket-consumer)
11. [Workspace Team Group Auto-Provisioning](#11-workspace-team-group-auto-provisioning)
12. [Frontend Architecture](#12-frontend-architecture)
13. [Zustand Micro-Stores](#13-zustand-micro-stores)
14. [UI/UX Specifications](#14-uiux-specifications)
15. [Migration Strategy](#15-migration-strategy)
16. [File Map](#16-file-map)
17. [Implementation Phases](#17-implementation-phases)

---

## 1. Introduction

### Purpose

Chat v2 is a complete rebuild of the Kraivor workspace messaging system. The legacy system was workspace-bound, used DynamoDB without ordering guarantees, had no seq-based protocol, and used a per-room WebSocket connection model that could not support reconnection sync.

The new architecture is **user-centric**, **seq-ordered**, **single-table DynamoDB**, with a **global WebSocket** connection and **micro-store** frontend state.

### Goals

| Goal | Metric |
|------|--------|
| Message ordering | Strict seq-based, no race conditions |
| Reconnection | Delta catch-up via seq sync, no bulk HTTP pull |
| Frontend rendering | Virtualized list, only visible items in DOM |
| State updates | O(1) message lookups via Map-based stores |
| Scaling | Single DynamoDB table with type discriminator, unlimited message volume |
| Topology | User-centric: DMs, Groups, Workspace Teams all first-class |

---

## 2. Topology

### Legacy (Deprecated)

```
Workspace
├── Chat
│   ├── Channel (workspace-bound)
│   ├── DM (workspace-bound)
│   └── Group (workspace-bound)
```

### New (User-Centric)

```
User
├── Direct Messages       (global — not workspace-bound)
├── Groups                (user-created, public/private — independent)
├── Workspace Team Groups (exactly ONE per workspace, auto-provisioned,
│                          membership syncs with workspace membership)
├── AI Chats              (isolated LLM state contexts — FastAPI service)
└── Archived Chats        (any room type moved to archive)
```

### Key Invariants

- A **Workspace** automatically provisions exactly ONE `WORKSPACE_TEAM` room on creation
- Joining/leaving a workspace **atomically** syncs membership to its team group via Django signals
- Deleting a workspace sets its team group to **Archived** status (not hard-deleted)
- DMs are **global** — the same pair of users share one DM room regardless of workspace
- Groups are **sovereign** — no parent workspace, created by users, can be public or private
- No sub-channels exist anywhere. Flattened room model.

---

## 3. Multi-Store Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CLIENT (Next.js)                             │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────────┐   │
│  │ ChatRoomPage│  │ chatStore    │  │ ChatSocket (global WS)    │   │
│  │ (virtualized│  │ messageStore │  │ SUBSCRIBE / SEND / SYNC   │   │
│  │  message    │  │ presenceStore│  │ protocol over single conn │   │
│  │  list)      │  │ typingStore  │  └───────────────────────────┘   │
│  │             │  │ uploadStore  │                                  │
│  └─────────────┘  └──────────────┘                                  │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
              ┌───────────┼───────────────┐
              │           │               │
         REST API    WebSocket         S3 Presigned
         (history,   (real-time         URLs
          search,     messaging,        (upload/
          CRUD)       presence)          download)
              │           │               │
              ▼           ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CORE SERVICE (Django)                        │
│                                                                   │
│  ┌──────────────────────┐  ┌─────────────────────────────────┐   │
│  │  PostgreSQL           │  │  DynamoDB (single table)        │   │
│  │  ─────────────        │  │  ─────────────────────          │   │
│  │  · Room metadata      │  │  · Messages (type=MSG)          │   │
│  │  · RoomMember         │  │  · Thread replies (THREAD)      │   │
│  │  · Roles & Permissions│  │  · Reactions (REACT)            │   │
│  │  · Pinned messages    │  │  · Read receipts (READ)         │   │
│  │  · Drafts             │  │  · Mentions (MENTION)           │   │
│  │  · Scheduled messages │  │  · Message edits (EDIT)         │   │
│  │  · Unread counters    │  │  · Deleted metadata (DELETE)    │   │
│  │  · Invites            │  │  · Polls (POLL)                 │   │
│  │  · Notification prefs │  │  · Voice notes (VOICE)          │   │
│  └──────────────────────┘  │  · Emoji reactions (EMOJI)       │   │
│                             └──────────────┬──────────────────┘   │
│                                            │                      │
│  ┌─────────────────────────────────────────┴──────────────────┐   │
│  │  Redis                                                    │   │
│  │  ──────                                                   │   │
│  │  · Presence (presence:user:{id} → ONLINE/AWAY/DND)        │   │
│  │  · Typing indicators (typing:room:{id} → Set<user_id>)    │   │
│  │  · Active voice sessions                                  │   │
│  │  · Socket room membership (Django Channels group)         │   │
│  │  · Read cache (room:{id}:last_seq → N)                   │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  S3 (via django-storages + pre-signed URLs)               │   │
│  │  ─────────────────────────────────────────────             │   │
│  │  · Images · Videos · PDFs · Files · Voice recordings      │   │
│  │  · Screen recordings                                       │   │
│  └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Store Selection Rationale

| Store | Why | Why Not the Other |
|-------|-----|-------------------|
| **PostgreSQL** for metadata | Relational queries (rooms by user, role lookups, workspace→room joins), ACID for membership sync | DynamoDB lacks joins, transactions are limited |
| **DynamoDB** for messages | Infinite write scaling, no relational bloat, cursor pagination built-in | PostgreSQL would slow under billions of rows, vacuum overhead |
| **Redis** for real-time state | TTL-based expiry, sub-millisecond reads, Pub/Sub for presence broadcast | Persistent stores would accumulate stale data |
| **S3** for assets | Designed for binary blobs, CDN-friendly, cost-effective | Database BLOBs would bloat backups, slow queries |

---

## 4. PostgreSQL Data Models

All models inherit `TimestampedModel` from `workspaces.models` (UUID PK, soft-delete, `created_at`/`updated_at`).

### 4.1 Room

```python
class Room(TimestampedModel):
    """Polymorphic room: DM, GROUP, WORKSPACE_TEAM, or AI."""

    class Type(models.TextChoices):
        DM = "DM", "Direct Message"
        GROUP = "GROUP", "Group"
        WORKSPACE_TEAM = "WORKSPACE_TEAM", "Workspace Team"
        AI = "AI", "AI Chat"

    room_type = models.CharField(max_length=20, choices=Type.choices)
    name = models.CharField(max_length=255)
    topic = models.TextField(blank=True, default="")
    is_public = models.BooleanField(default=False)  # for GROUP only

    # Only set for WORKSPACE_TEAM — all other types are workspace-agnostic
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="team_group",
    )

    created_by = models.UUIDField()

    # Denormalized counters (avoid expensive COUNT queries)
    member_count = models.IntegerField(default=1)
    message_count = models.IntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_message_content = models.TextField(blank=True, default="")
    last_message_sender_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "chat_rooms"
        indexes = [
            models.Index(fields=["room_type", "-last_message_at"], name="idx_room_type_recent"),
            models.Index(fields=["workspace_id"], name="idx_room_workspace"),
            models.Index(fields=["created_by"], name="idx_room_creator"),
            models.Index(fields=["is_public", "room_type"], name="idx_room_public_type"),
        ]
```

### 4.2 RoomMember

```python
class RoomMember(TimestampedModel):
    """Membership + unread tracking via last_read_seq."""

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="members")
    user_id = models.UUIDField()
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_seq = models.BigIntegerField(default=0)

    class Meta:
        db_table = "chat_room_members"
        constraints = [
            models.UniqueConstraint(
                fields=["room", "user_id"],
                name="uq_room_member",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "room"], name="idx_member_user_room"),
            models.Index(fields=["user_id", "-joined_at"], name="idx_member_user_recent"),
        ]
```

### 4.3 Role

```python
class Role(models.Model):
    """Custom role with granular boolean permissions."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default="#9898a6")  # hex for member list
    priority = models.PositiveSmallIntegerField(default=0)  # higher = higher display rank

    # Permission flags
    can_delete_messages = models.BooleanField(default=False)
    can_pin_messages = models.BooleanField(default=False)
    can_manage_members = models.BooleanField(default=False)
    can_manage_roles = models.BooleanField(default=False)
    can_share_repositories = models.BooleanField(default=False)
    can_view_audit_logs = models.BooleanField(default=False)

    class Meta:
        db_table = "chat_roles"
        indexes = [
            models.Index(fields=["room", "priority"], name="idx_role_room_priority"),
        ]
```

### 4.4 RoomMemberRole

```python
class RoomMemberRole(models.Model):
    """Junction: members can hold multiple roles."""

    member = models.ForeignKey(RoomMember, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        db_table = "chat_member_roles"
        constraints = [
            models.UniqueConstraint(
                fields=["member", "role"],
                name="uq_member_role",
            ),
        ]
```

### 4.5 PinnedMessage

```python
class PinnedMessage(models.Model):
    """Pinned messages — stored in PostgreSQL for fast lookup."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="pinned_messages")
    message_seq = models.BigIntegerField()          # seq in DynamoDB
    pinned_by = models.UUIDField()
    pinned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_pinned_messages"
        constraints = [
            models.UniqueConstraint(
                fields=["room", "message_seq"],
                name="uq_pinned_room_seq",
            ),
        ]
        indexes = [
            models.Index(fields=["room", "-pinned_at"], name="idx_pinned_room_recent"),
        ]
```

### 4.6 Draft

```python
class Draft(models.Model):
    """Per-user draft message per room."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="drafts")
    user_id = models.UUIDField()
    content = models.TextField(blank=True, default="")
    reply_to_seq = models.BigIntegerField(null=True, blank=True)
    attachment_urls = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_drafts"
        constraints = [
            models.UniqueConstraint(
                fields=["room", "user_id"],
                name="uq_draft_room_user",
            ),
        ]
```

### 4.7 ScheduledMessage

```python
class ScheduledMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    sender_id = models.UUIDField()
    content = models.TextField()
    attachment_urls = models.JSONField(default=list)
    send_at = models.DateTimeField(db_index=True)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_scheduled_messages"
        indexes = [
            models.Index(fields=["send_at", "is_sent"], name="idx_scheduled_pending"),
        ]
```

### 4.8 RoomInvite

```python
class RoomInvite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="invites")
    invited_by = models.UUIDField()
    target_user_id = models.UUIDField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("ACCEPTED", "Accepted"), ("EXPIRED", "Expired")],
        default="PENDING",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "chat_room_invites"
        indexes = [
            models.Index(fields=["target_user_id", "status"], name="idx_invite_user_status"),
        ]
```

---

## 5. DynamoDB Single-Table Design

### 5.1 Table Schema

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| `room_id` | String | **Partition Key** | UUID of the room |
| `sort_key` | String | **Sort Key** | `{type}#{seq:020d}` — zero-padded for string sort |
| `type` | String | — | Discriminator: `MSG`, `THREAD`, `REACT`, `EDIT`, `READ`, `MENTION`, `DELETE`, `POLL`, `VOICE`, `EMOJI` |
| `seq` | Number | — | Monotonic integer per room |
| `data` | Map | — | Type-specific payload (see below) |
| `created_at` | String | — | ISO 8601 |

### 5.2 Sort Key Format

```
{type}#{seq:020d}

Examples:
  MSG#00000000000000000001        # first message in room
  MSG#00000000000000000042        # 42nd message
  THREAD#00000000000000000001#00000000000000000001  # reply to msg 1
  REACT#00000000000000000001      # reaction on msg 1
  EDIT#00000000000000000001       # edit to msg 1
  READ#00000000000000000042       # read receipt up to seq 42
  DELETE#00000000000000000001     # deletion record for msg 1
```

### 5.3 Type-Specific Payloads

**MSG** — Message content
```json
{
  "type": "MSG",
  "seq": 1,
  "message_id": "uuid",
  "sender_id": "uuid",
  "sender_name": "alice",
  "content": "Hello world",
  "reply_to_seq": null,
  "mention_user_ids": [],
  "attachment_urls": [],
  "is_edited": false,
  "created_at": "2026-07-09T12:00:00Z"
}
```

**THREAD** — Thread reply (parent reference via sort_key prefix)
```json
{
  "type": "THREAD",
  "seq": 2,
  "message_id": "uuid",
  "parent_seq": 1,
  "sender_id": "uuid",
  "sender_name": "bob",
  "content": "I agree!",
  "mention_user_ids": [],
  "attachment_urls": [],
  "created_at": "2026-07-09T12:01:00Z"
}
```

**REACT** — Reaction (upsert idempotent)
```json
{
  "type": "REACT",
  "seq": 3,
  "target_seq": 1,
  "user_id": "uuid",
  "emoji": "👍",
  "created_at": "2026-07-09T12:02:00Z"
}
```

**EDIT** — Edit history entry
```json
{
  "type": "EDIT",
  "seq": 4,
  "target_seq": 1,
  "previous_content": "Hello world",
  "new_content": "Hello **everyone**",
  "edited_by": "uuid",
  "edited_at": "2026-07-09T12:05:00Z"
}
```

**READ** — Per-user read receipt
```json
{
  "type": "READ",
  "reader_id": "uuid",
  "read_up_to_seq": 42,
  "read_at": "2026-07-09T12:06:00Z"
}
```

### 5.4 Key Query Patterns

```
# Get all messages in a room (newest first)
Query:
  KeyConditionExpression: "room_id = :rid AND begins_with(sort_key, :prefix)"
  ExpressionAttributeValues: { ":rid": room_id, ":prefix": "MSG#" }
  ScanIndexForward: false
  Limit: 50

# Get thread replies for a parent message
Query:
  KeyConditionExpression: "room_id = :rid AND begins_with(sort_key, :prefix)"
  ExpressionAttributeValues: { ":rid": room_id, ":prefix": "THREAD#00000000000000000001#" }
  ScanIndexForward: true

# Get reactions on a message
Query:
  KeyConditionExpression: "room_id = :rid AND sort_key BETWEEN :start AND :end"
  ExpressionAttributeValues: { ":rid": room_id, ":start": "REACT#00000000000000000001", ":end": "REACT#00000000000000000001~" }

# Get messages since seq N (for sync protocol)
Query:
  KeyConditionExpression: "room_id = :rid AND sort_key > :since"
  ExpressionAttributeValues: { ":rid": room_id, ":since": "MSG#00000000000000000042" }
  Limit: 200
```

### 5.5 DynamoDB Repository

```python
# services/core/apps/chat/dynamodb/repository.py

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import boto3
from botocore.exceptions import ClientError
from django.conf import settings


class ChatMessageRepository:
    """Single-table DynamoDB repository for all chat entities."""

    TYPE_MESSAGE = "MSG"
    TYPE_THREAD = "THREAD"
    TYPE_REACTION = "REACT"
    TYPE_EDIT = "EDIT"
    TYPE_READ = "READ"
    TYPE_DELETION = "DELETE"

    def __init__(self):
        self._table = boto3.resource(
            "dynamodb",
            region_name=settings.AWS_REGION,
        ).Table(settings.DYNAMODB_CHAT_TABLE)

    # ─── Atomic Seq Counter ───────────────────────────────────────

    def allocate_seq(self, room_id: str) -> int:
        """Atomically allocate the next seq number for a room.

        Uses DynamoDB UpdateItem with ADD on a counter item.
        Counter item: room_id={room_id}, sort_key='_counter'
        """
        response = self._table.update_item(
            Key={"room_id": room_id, "sort_key": "_counter"},
            UpdateExpression="ADD #val :inc",
            ExpressionAttributeNames={"#val": "next_seq"},
            ExpressionAttributeValues={":inc": 1},
            ReturnValues="UPDATED_NEW",
        )
        return response["Attributes"]["next_seq"]

    def init_counter(self, room_id: str) -> None:
        """Initialize counter for a new room (seq starts at 1)."""
        self._table.put_item(
            Item={
                "room_id": room_id,
                "sort_key": "_counter",
                "next_seq": 1,
            },
            ConditionExpression="attribute_not_exists(sort_key)",
        )

    # ─── Write Operations ─────────────────────────────────────────

    def put_message(
        self,
        *,
        room_id: str,
        seq: int,
        sender_id: str,
        sender_name: str,
        content: str,
        reply_to_seq: int | None = None,
        mention_user_ids: list[str] | None = None,
        attachment_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        sort_key = f"MSG#{seq:020d}"
        item: dict[str, Any] = {
            "room_id": room_id,
            "sort_key": sort_key,
            "type": self.TYPE_MESSAGE,
            "seq": seq,
            "message_id": str(uuid.uuid4()),
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": content,
            "reply_to_seq": reply_to_seq,
            "mention_user_ids": mention_user_ids or [],
            "attachment_urls": attachment_urls or [],
            "is_edited": False,
            "created_at": datetime.now(tz=UTC).isoformat(),
        }
        self._table.put_item(Item=item)
        return item

    def put_thread_reply(
        self,
        *,
        room_id: str,
        seq: int,
        parent_seq: int,
        sender_id: str,
        sender_name: str,
        content: str,
        mention_user_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        sort_key = f"THREAD#{parent_seq:020d}#{seq:020d}"
        item: dict[str, Any] = {
            "room_id": room_id,
            "sort_key": sort_key,
            "type": self.TYPE_THREAD,
            "seq": seq,
            "parent_seq": parent_seq,
            "message_id": str(uuid.uuid4()),
            "sender_id": sender_id,
            "sender_name": sender_name,
            "content": content,
            "mention_user_ids": mention_user_ids or [],
            "created_at": datetime.now(tz=UTC).isoformat(),
        }
        self._table.put_item(Item=item)
        return item

    def put_reaction(
        self,
        *,
        room_id: str,
        seq: int,
        target_seq: int,
        user_id: str,
        emoji: str,
    ) -> dict[str, Any]:
        sort_key = f"REACT#{target_seq:020d}#{user_id}#{emoji}"
        item: dict[str, Any] = {
            "room_id": room_id,
            "sort_key": sort_key,
            "type": self.TYPE_REACTION,
            "seq": seq,
            "target_seq": target_seq,
            "user_id": user_id,
            "emoji": emoji,
            "created_at": datetime.now(tz=UTC).isoformat(),
        }
        self._table.put_item(Item=item)
        return item

    def put_edit_record(
        self,
        *,
        room_id: str,
        seq: int,
        target_seq: int,
        previous_content: str,
        new_content: str,
        edited_by: str,
    ) -> dict[str, Any]:
        sort_key = f"EDIT#{target_seq:020d}#{seq:020d}"
        item: dict[str, Any] = {
            "room_id": room_id,
            "sort_key": sort_key,
            "type": self.TYPE_EDIT,
            "seq": seq,
            "target_seq": target_seq,
            "previous_content": previous_content,
            "new_content": new_content,
            "edited_by": edited_by,
            "edited_at": datetime.now(tz=UTC).isoformat(),
        }
        self._table.put_item(Item=item)
        return item

    def put_read_receipt(
        self,
        *,
        room_id: str,
        reader_id: str,
        read_up_to_seq: int,
    ) -> dict[str, Any]:
        sort_key = f"READ#{reader_id}"
        item: dict[str, Any] = {
            "room_id": room_id,
            "sort_key": sort_key,
            "type": self.TYPE_READ,
            "reader_id": reader_id,
            "read_up_to_seq": read_up_to_seq,
            "read_at": datetime.now(tz=UTC).isoformat(),
        }
        self._table.put_item(Item=item)
        return item

    # ─── Query Operations ─────────────────────────────────────────

    def get_messages(
        self,
        room_id: str,
        limit: int = 50,
        after_seq: int | None = None,
        before_seq: int | None = None,
    ) -> tuple[list[dict[str, Any]], int | None]:
        """Get messages in a room, ordered by seq descending.

        Returns (items, last_evaluated_seq) for cursor pagination.
        """
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": (
                "room_id = :rid AND begins_with(sort_key, :prefix)"
            ),
            "ExpressionAttributeValues": {
                ":rid": room_id,
                ":prefix": "MSG#",
            },
            "Limit": limit,
            "ScanIndexForward": False,  # newest first
        }

        if before_seq is not None:
            # Pagination: get messages before this seq
            kwargs["ExclusiveStartKey"] = {
                "room_id": room_id,
                "sort_key": f"MSG#{before_seq:020d}",
            }

        response = self._table.query(**kwargs)
        items = response.get("Items", [])
        last_key = response.get("LastEvaluatedKey")

        last_seq = None
        if last_key:
            # Extract seq from sort_key (MSG#00000000000000000042)
            last_seq = int(last_key["sort_key"].split("#")[1])

        return items, last_seq

    def get_messages_since(
        self, room_id: str, since_seq: int, limit: int = 200
    ) -> list[dict[str, Any]]:
        """Get messages with seq > since_seq (for sync protocol)."""
        response = self._table.query(
            KeyConditionExpression=(
                "room_id = :rid AND sort_key > :since"
            ),
            ExpressionAttributeValues={
                ":rid": room_id,
                ":since": f"MSG#{since_seq:020d}",
            },
            Limit=limit,
            ScanIndexForward=True,  # oldest first
        )
        return response.get("Items", [])

    def get_thread_replies(
        self, room_id: str, parent_seq: int
    ) -> list[dict[str, Any]]:
        response = self._table.query(
            KeyConditionExpression=(
                "room_id = :rid AND begins_with(sort_key, :prefix)"
            ),
            ExpressionAttributeValues={
                ":rid": room_id,
                ":prefix": f"THREAD#{parent_seq:020d}#",
            },
            ScanIndexForward=True,
        )
        return response.get("Items", [])

    def get_reactions(
        self, room_id: str, target_seq: int
    ) -> list[dict[str, Any]]:
        response = self._table.query(
            KeyConditionExpression=(
                "room_id = :rid AND begins_with(sort_key, :prefix)"
            ),
            ExpressionAttributeValues={
                ":rid": room_id,
                ":prefix": f"REACT#{target_seq:020d}#",
            },
        )
        return response.get("Items", [])

    # ─── Update Operations ────────────────────────────────────────

    def update_message_content(
        self, room_id: str, seq: int, new_content: str
    ) -> None:
        self._table.update_item(
            Key={
                "room_id": room_id,
                "sort_key": f"MSG#{seq:020d}",
            },
            UpdateExpression="SET #c = :content, is_edited = :true",
            ExpressionAttributeNames={"#c": "content"},
            ExpressionAttributeValues={
                ":content": new_content,
                ":true": True,
            },
        )

    def soft_delete_message(self, room_id: str, seq: int) -> None:
        """Mark message as deleted. Content is preserved for audit but
        returned as '[deleted]' to non-admin users."""
        self._table.update_item(
            Key={
                "room_id": room_id,
                "sort_key": f"MSG#{seq:020d}",
            },
            UpdateExpression="SET is_deleted = :true, deleted_at = :now",
            ExpressionAttributeValues={
                ":true": True,
                ":now": datetime.now(tz=UTC).isoformat(),
            },
        )

    # ─── Read Receipt ─────────────────────────────────────────────

    def get_read_receipt(
        self, room_id: str, reader_id: str
    ) -> dict[str, Any] | None:
        response = self._table.get_item(
            Key={
                "room_id": room_id,
                "sort_key": f"READ#{reader_id}",
            },
        )
        return response.get("Item")
```

---

## 6. Redis State Layer

### Keyspace Design

| Key Pattern | Type | TTL | Description |
|------------|------|-----|-------------|
| `presence:user:{user_id}` | String | 60s | `ONLINE`, `AWAY`, `DND`, or `OFFLINE` |
| `typing:room:{room_id}` | Set | 5s | Set of user IDs currently typing |
| `typing:room:{room_id}:last:{user_id}` | String | 5s | Timestamp of last typing dispatch (for throttling) |
| `voice:room:{room_id}` | Set | — | Users in active voice session |
| `cache:room:{room_id}:latest_seq` | String | — | Cached latest seq to avoid DynamoDB query |

### Typing Throttling

```python
# Redis-backed typing throttle: max 1 dispatch per 2.5s per user per room
# Returns True if should dispatch, False if throttled

async def should_dispatch_typing(redis, room_id: str, user_id: str) -> bool:
    key = f"typing:room:{room_id}:last:{user_id}"
    last = await redis.get(key)
    now = time.time()
    if last and (now - float(last)) < 2.5:
        return False
    await redis.setex(key, 5, str(now))
    return True
```

### Presence Lifecycle

```
WebSocket CONNECT
  → SETEX presence:user:{id} 60 "ONLINE"
  → PUBLISH to user's notification group

Heartbeat (every 30s)
  → EXPIRE presence:user:{id} 60

WebSocket DISCONNECT
  → PUBLISH presence:user:{id} "OFFLINE"
  → DEL presence:user:{id}
  → DEL typing:room:*:{id}  # cleanup typing state

AWAY detection (server-side, after 5min no heartbeat)
  → SET presence:user:{id} "AWAY" EX 60
```

---

## 7. S3 Asset Storage

### File Upload Flow

```
Client                     Server                      S3
  │                          │                          │
  ├─ POST /api/chat/upload   │                          │
  │  { file_name, mime, size}│                          │
  │─────────────────────────►│                          │
  │                          │ Generate pre-signed URL  │
  │                          │─────────────────────────►│
  │                          │◄─────────────────────────│
  │◄── { upload_url, file_id }                          │
  │                          │                          │
  ├─ PUT {file} ───────────────────────────────────────►│
  │◄────────────────────────────────────────────────────│
  │                          │                          │
  ├─ POST /api/chat/confirm  │                          │
  │  { file_id }             │                          │
  │─────────────────────────►│                          │
  │                          │ Generate public URL      │
  │                          │─────────────────────────►│
  │                          │◄─────────────────────────│
  │◄── { public_url }        │                          │
```

### Django View (S3 Presigned Upload)

```python
# services/core/apps/chat/views/uploads.py

import uuid
import boto3
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class PresignedUploadView(APIView):
    """Generate a pre-signed S3 URL for direct client upload."""

    def post(self, request):
        file_id = str(uuid.uuid4())
        ext = request.data.get("file_name", "").rsplit(".", 1)[-1]
        key = f"chat/{file_id}.{ext}"

        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.AWS_CHAT_BUCKET,
                "Key": key,
                "ContentType": request.data.get("mime", "application/octet-stream"),
            },
            ExpiresIn=3600,
        )
        return Response({"upload_url": url, "file_id": file_id, "key": key})
```

---

## 8. Atomic Seq Counter

### How It Works

Each room has a counter item in DynamoDB:
```
{ "room_id": "uuid", "sort_key": "_counter", "next_seq": 42 }
```

When a message is sent:
1. Call `allocate_seq(room_id)` → DynamoDB `UpdateItem ADD next_seq :inc`
2. Use returned seq value as the message's sort key suffix
3. Write the message item

### Why This Works

- **Atomicity**: DynamoDB `UpdateItem` with `ADD` is an atomic operation. Two concurrent sends get different seq numbers.
- **Monotonic**: Seq always increases. No gaps unless a write fails after counter increment (acceptable — seqs are ordering keys, not invoice numbers).
- **No hot partition concern**: Counter items are tiny (few bytes). DynamoDB Adaptive Capacity handles them efficiently even on busy rooms.

### Counter Initialization

When a room is created, `init_counter(room_id)` seeds the counter item with `next_seq=1`. This is idempotent via `ConditionExpression: attribute_not_exists(sort_key)`.

---

## 9. WebSocket Protocol

### Connection

```
ws://host/ws/chat/?token={jwt}

Single global connection per user. No room_id in URL path.
```

### Client → Server Actions

```typescript
// Subscribe to a room with optional catch-up seq
{
  action: "SUBSCRIBE",
  room_id: "0194f8c2-...",
  last_seen_seq: 42
}

// Send a message
{
  action: "SEND",
  room_id: "0194f8c2-...",
  content: "Hello **world**",
  reply_to_seq: 41,
  mention_user_ids: [],
  attachment_urls: []
}

// Send a thread reply
{
  action: "THREAD_REPLY",
  room_id: "0194f8c2-...",
  parent_seq: 1,
  content: "I agree!",
  mention_user_ids: []
}

// Add a reaction
{
  action: "REACT",
  room_id: "0194f8c2-...",
  target_seq: 1,
  emoji: "👍"
}

// Edit a message
{
  action: "EDIT",
  room_id: "0194f8c2-...",
  seq: 48,
  content: "Edited content"
}

// Delete a message
{
  action: "DELETE",
  room_id: "0194f8c2-...",
  seq: 48
}

// Typing indicator
{
  action: "TYPING",
  room_id: "0194f8c2-...",
  status: "START" | "STOP"
}

// Mark room as read
{
  action: "MARK_READ",
  room_id: "0194f8c2-...",
  upto_seq: 48
}

// Bulk sync on reconnect
{
  action: "SYNC_ROOMS",
  rooms: [
    { room_id: "0194f8c2-...", last_seen_seq: 42 },
    { room_id: "0194f8c3-...", last_seen_seq: 17 }
  ]
}

// Presence update
{
  action: "PRESENCE",
  status: "ONLINE" | "AWAY" | "DND" | "OFFLINE"
}

// Heartbeat (every 30s)
{
  action: "HEARTBEAT"
}
```

### Server → Client Events

```typescript
// Initial connection response
{
  type: "CONNECTED",
  user_id: "0194f8c2-...",
  rooms: [
    { room_id: "0194f8c2-...", last_seq: 142 },
    { room_id: "0194f8c3-...", last_seq: 87 }
  ],
  server_time: "2026-07-09T12:00:00Z"
}

// Delta sync (response to SUBSCRIBE or SYNC_ROOMS)
{
  type: "SYNC",
  room_id: "0194f8c2-...",
  messages: [
    {
      seq: 43,
      message_id: "uuid",
      sender_id: "uuid",
      sender_name: "bob",
      content: "Hey!",
      reply_to_seq: null,
      mention_user_ids: [],
      attachment_urls: [],
      is_edited: false,
      created_at: "2026-07-09T12:00:00Z"
    }
  ],
  upto_seq: 48
}

// New message broadcast
{
  type: "MESSAGE",
  room_id: "0194f8c2-...",
  seq: 48,
  message_id: "uuid",
  sender_id: "uuid",
  sender_name: "bob",
  content: "Message text",
  reply_to_seq: null,
  mention_user_ids: [],
  attachment_urls: [],
  is_edited: false,
  created_at: "2026-07-09T12:00:00Z"
}

// Thread reply broadcast
{
  type: "THREAD_REPLY",
  room_id: "0194f8c2-...",
  seq: 49,
  parent_seq: 1,
  message_id: "uuid",
  sender_id: "uuid",
  sender_name: "alice",
  content: "Thread reply",
  created_at: "2026-07-09T12:01:00Z"
}

// Reaction broadcast
{
  type: "REACTION",
  room_id: "0194f8c2-...",
  target_seq: 1,
  user_id: "uuid",
  user_name: "charlie",
  emoji: "👍"
}

// Message edited broadcast
{
  type: "MESSAGE_EDITED",
  room_id: "0194f8c2-...",
  seq: 48,
  content: "Edited text"
}

// Message deleted broadcast
{
  type: "MESSAGE_DELETED",
  room_id: "0194f8c2-...",
  seq: 48
}

// Typing indicator
{
  type: "TYPING",
  room_id: "0194f8c2-...",
  user_id: "uuid",
  user_name: "dave",
  status: "START" | "STOP"
}

// Presence change
{
  type: "PRESENCE",
  user_id: "uuid",
  status: "ONLINE" | "AWAY" | "DND" | "OFFLINE"
}

// Error
{
  type: "ERROR",
  code: "ROOM_NOT_FOUND" | "PERMISSION_DENIED" | "RATE_LIMITED",
  message: "You are not a member of this room."
}
```

---

## 10. WebSocket Consumer

```python
# services/core/apps/chat/consumers.py

import json
from datetime import UTC, datetime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import transaction

from .dynamodb.repository import ChatMessageRepository
from .models import Message, Room, RoomMember

TYPING_COOLDOWN = 2.5  # seconds


class ChatConsumer(AsyncWebsocketConsumer):
    """Global WebSocket consumer for real-time chat."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id: str | None = None
        self.user_group: str | None = None
        self.subscribed_rooms: set[str] = set()
        self.last_typing_at: dict[str, float] = {}
        self.repo = ChatMessageRepository()

    async def connect(self):
        self.user_id = self.scope.get("user_id")
        if not self.user_id:
            await self.close(code=4001)
            return

        self.user_group = f"user_{self.user_id}"
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()

        # Send CONNECTED with all rooms and their latest seq
        rooms = await self._get_user_rooms()
        await self.send_json({
            "type": "CONNECTED",
            "user_id": self.user_id,
            "rooms": rooms,
            "server_time": datetime.now(tz=UTC).isoformat(),
        })

    async def disconnect(self, close_code):
        for room_id in list(self.subscribed_rooms):
            await self.channel_layer.group_discard(f"room_{room_id}", self.channel_name)
        self.subscribed_rooms.clear()

        await self.channel_layer.group_send(
            self.user_group,
            {"type": "presence.broadcast", "status": "OFFLINE", "user_id": self.user_id},
        )
        await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        action = data.get("action")
        handler = {
            "SUBSCRIBE": self._handle_subscribe,
            "SEND": self._handle_send,
            "THREAD_REPLY": self._handle_thread_reply,
            "REACT": self._handle_reaction,
            "EDIT": self._handle_edit,
            "DELETE": self._handle_delete,
            "TYPING": self._handle_typing,
            "MARK_READ": self._handle_mark_read,
            "SYNC_ROOMS": self._handle_sync_rooms,
            "HEARTBEAT": self._handle_heartbeat,
            "PRESENCE": self._handle_presence,
        }.get(action)

        if handler:
            await handler(data)

    # ─── Handlers ─────────────────────────────────────────────────

    async def _handle_subscribe(self, data: dict):
        room_id = data["room_id"]
        last_seen_seq = data.get("last_seen_seq", 0)

        is_member = await self._is_member(room_id)
        if not is_member:
            await self.send_json({"type": "ERROR", "code": "PERMISSION_DENIED",
                                  "message": "Not a member."})
            return

        await self.channel_layer.group_add(f"room_{room_id}", self.channel_name)
        self.subscribed_rooms.add(room_id)

        messages = await self._get_messages_since(room_id, last_seen_seq)
        upto_seq = messages[-1]["seq"] if messages else last_seen_seq

        await self.send_json({
            "type": "SYNC",
            "room_id": room_id,
            "messages": messages,
            "upto_seq": upto_seq,
        })

    async def _handle_send(self, data: dict):
        room_id = data["room_id"]

        if not await self._is_member(room_id):
            return

        seq = self.repo.allocate_seq(room_id)
        msg_item = self.repo.put_message(
            room_id=room_id,
            seq=seq,
            sender_id=self.user_id,
            sender_name=self.scope.get("user_name", ""),
            content=data["content"],
            reply_to_seq=data.get("reply_to_seq"),
            mention_user_ids=data.get("mention_user_ids", []),
            attachment_urls=data.get("attachment_urls", []),
        )

        await self._update_room_metadata(room_id, data["content"], seq)

        await self.channel_layer.group_send(
            f"room_{room_id}",
            {
                "type": "chat.message",
                "room_id": room_id,
                "message": msg_item,
                "_exclude_user_id": self.user_id,
            },
        )

    async def _handle_thread_reply(self, data: dict):
        room_id = data["room_id"]
        if not await self._is_member(room_id):
            return

        seq = self.repo.allocate_seq(room_id)
        reply_item = self.repo.put_thread_reply(
            room_id=room_id,
            seq=seq,
            parent_seq=data["parent_seq"],
            sender_id=self.user_id,
            sender_name=self.scope.get("user_name", ""),
            content=data["content"],
            mention_user_ids=data.get("mention_user_ids", []),
        )

        await self.channel_layer.group_send(
            f"room_{room_id}",
            {
                "type": "chat.thread_reply",
                "room_id": room_id,
                "reply": reply_item,
                "_exclude_user_id": self.user_id,
            },
        )

    async def _handle_reaction(self, data: dict):
        room_id = data["room_id"]
        if not await self._is_member(room_id):
            return

        seq = self.repo.allocate_seq(room_id)
        self.repo.put_reaction(
            room_id=room_id,
            seq=seq,
            target_seq=data["target_seq"],
            user_id=self.user_id,
            emoji=data["emoji"],
        )

        await self.channel_layer.group_send(
            f"room_{room_id}",
            {
                "type": "chat.reaction",
                "room_id": room_id,
                "target_seq": data["target_seq"],
                "user_id": self.user_id,
                "user_name": self.scope.get("user_name", ""),
                "emoji": data["emoji"],
                "_exclude_user_id": self.user_id,
            },
        )

    async def _handle_edit(self, data: dict):
        room_id = data["room_id"]
        seq = data["seq"]
        new_content = data["content"]

        if not await self._is_member(room_id):
            return

        edit_seq = self.repo.allocate_seq(room_id)
        self.repo.update_message_content(room_id, seq, new_content)
        self.repo.put_edit_record(
            room_id=room_id,
            seq=edit_seq,
            target_seq=seq,
            previous_content="",  # could fetch old content if needed
            new_content=new_content,
            edited_by=self.user_id,
        )

        await self.channel_layer.group_send(
            f"room_{room_id}",
            {
                "type": "chat.message_edited",
                "room_id": room_id,
                "seq": seq,
                "content": new_content,
                "_exclude_user_id": self.user_id,
            },
        )

    async def _handle_delete(self, data: dict):
        room_id = data["room_id"]
        seq = data["seq"]

        if not await self._is_member(room_id):
            return

        self.repo.soft_delete_message(room_id, seq)

        await self.channel_layer.group_send(
            f"room_{room_id}",
            {
                "type": "chat.message_deleted",
                "room_id": room_id,
                "seq": seq,
                "_exclude_user_id": self.user_id,
            },
        )

    async def _handle_typing(self, data: dict):
        room_id = data["room_id"]
        status = data["status"]

        # Throttle: max 1 START per 2.5s
        if status == "START":
            now = datetime.now(tz=UTC).timestamp()
            last = self.last_typing_at.get(room_id, 0)
            if now - last < TYPING_COOLDOWN:
                return
            self.last_typing_at[room_id] = now

        await self.channel_layer.group_send(
            f"room_{room_id}",
            {
                "type": "typing.broadcast",
                "room_id": room_id,
                "user_id": self.user_id,
                "user_name": self.scope.get("user_name", ""),
                "status": status,
                "_exclude_user_id": self.user_id,
            },
        )

    async def _handle_mark_read(self, data: dict):
        room_id = data["room_id"]
        upto_seq = data["upto_seq"]

        self.repo.put_read_receipt(
            room_id=room_id,
            reader_id=self.user_id,
            read_up_to_seq=upto_seq,
        )
        await self._update_read_seq(room_id, upto_seq)

    async def _handle_sync_rooms(self, data: dict):
        rooms = data.get("rooms", [])
        for entry in rooms:
            room_id = entry["room_id"]
            last_seq = entry.get("last_seen_seq", 0)
            messages = await self._get_messages_since(room_id, last_seq)
            upto_seq = messages[-1]["seq"] if messages else last_seq
            await self.send_json({
                "type": "SYNC",
                "room_id": room_id,
                "messages": messages,
                "upto_seq": upto_seq,
            })

    async def _handle_heartbeat(self, data: dict):
        # Presence TTL refresh happens via Redis SETEX in middleware
        pass

    async def _handle_presence(self, data: dict):
        await self.channel_layer.group_send(
            self.user_group,
            {"type": "presence.broadcast", "user_id": self.user_id, "status": data["status"]},
        )

    # ─── Broadcast Handlers ───────────────────────────────────────

    async def chat_message(self, event: dict):
        if event.pop("_exclude_user_id", None) == self.user_id:
            return
        event["type"] = "MESSAGE"
        await self.send_json({"type": "MESSAGE", "room_id": event["room_id"],
                              **event["message"]})

    async def chat_thread_reply(self, event: dict):
        if event.pop("_exclude_user_id", None) == self.user_id:
            return
        await self.send_json({"type": "THREAD_REPLY", "room_id": event["room_id"],
                              **event["reply"]})

    async def chat_reaction(self, event: dict):
        if event.pop("_exclude_user_id", None) == self.user_id:
            return
        await self.send_json({
            "type": "REACTION",
            "room_id": event["room_id"],
            "target_seq": event["target_seq"],
            "user_id": event["user_id"],
            "user_name": event["user_name"],
            "emoji": event["emoji"],
        })

    async def chat_message_edited(self, event: dict):
        if event.pop("_exclude_user_id", None) == self.user_id:
            return
        await self.send_json({
            "type": "MESSAGE_EDITED",
            "room_id": event["room_id"],
            "seq": event["seq"],
            "content": event["content"],
        })

    async def chat_message_deleted(self, event: dict):
        if event.pop("_exclude_user_id", None) == self.user_id:
            return
        await self.send_json({
            "type": "MESSAGE_DELETED",
            "room_id": event["room_id"],
            "seq": event["seq"],
        })

    async def typing_broadcast(self, event: dict):
        if event.pop("_exclude_user_id", None) == self.user_id:
            return
        await self.send_json({
            "type": "TYPING",
            "room_id": event["room_id"],
            "user_id": event["user_id"],
            "user_name": event["user_name"],
            "status": event["status"],
        })

    async def presence_broadcast(self, event: dict):
        await self.send_json({
            "type": "PRESENCE",
            "user_id": event["user_id"],
            "status": event["status"],
        })

    # ─── Database Helpers ─────────────────────────────────────────

    @database_sync_to_async
    def _is_member(self, room_id: str) -> bool:
        return RoomMember.objects.filter(
            room_id=room_id, user_id=self.user_id
        ).exists()

    @database_sync_to_async
    def _get_user_rooms(self) -> list[dict]:
        memberships = RoomMember.objects.filter(
            user_id=self.user_id
        ).select_related("room").only(
            "room_id", "last_read_seq", "room__last_message_at"
        )
        return [
            {"room_id": str(m.room_id), "last_seq": m.last_read_seq}
            for m in memberships
        ]

    async def _get_messages_since(
        self, room_id: str, since_seq: int
    ) -> list[dict]:
        items = await self.repo.get_messages_since(room_id, since_seq, limit=200)
        return items

    @database_sync_to_async
    def _update_room_metadata(
        self, room_id: str, content: str, seq: int
    ) -> None:
        Room.objects.filter(id=room_id).update(
            last_message_content=content[:255],
            last_message_sender_name=self.scope.get("user_name", ""),
            last_message_at=datetime.now(tz=UTC),
            message_count=models.F("message_count") + 1,
        )

    @database_sync_to_async
    def _update_read_seq(self, room_id: str, seq: int) -> None:
        RoomMember.objects.filter(
            room_id=room_id, user_id=self.user_id
        ).update(last_read_seq=seq)

    async def send_json(self, data: dict) -> None:
        await self.send(text_data=json.dumps(data))
```

---

## 11. Workspace Team Group Auto-Provisioning

### Signal Handlers

```python
# services/core/apps/chat/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.workspaces.models import Workspace, WorkspaceMember
from .models import Room, RoomMember


@receiver(post_save, sender=Workspace)
def provision_team_group(sender, instance, created, **kwargs):
    """Auto-create a WORKSPACE_TEAM room when a workspace is created."""
    if not created:
        return

    room = Room.objects.create(
        room_type=Room.Type.WORKSPACE_TEAM,
        name=f"{instance.name} Team",
        workspace=instance,
        created_by=instance.owner_id,
        is_public=False,
    )
    # Add the owner as the first member
    RoomMember.objects.create(room=room, user_id=instance.owner_id)

    # Initialize DynamoDB counter for the room
    from .dynamodb.repository import ChatMessageRepository
    ChatMessageRepository().init_counter(str(room.id))


@receiver(post_save, sender=WorkspaceMember)
def add_to_team_group(sender, instance, created, **kwargs):
    """When a user joins a workspace, also join the team group."""
    if not created:
        return

    team_room = Room.objects.filter(
        workspace_id=instance.workspace_id,
        room_type=Room.Type.WORKSPACE_TEAM,
    ).first()
    if team_room:
        RoomMember.objects.get_or_create(
            room=team_room,
            user_id=instance.user_id,
        )


@receiver(post_delete, sender=WorkspaceMember)
def remove_from_team_group(sender, instance, **kwargs):
    """When a user leaves a workspace, also leave the team group."""
    team_room = Room.objects.filter(
        workspace_id=instance.workspace_id,
        room_type=Room.Type.WORKSPACE_TEAM,
    ).first()
    if team_room:
        RoomMember.objects.filter(
            room=team_room,
            user_id=instance.user_id,
        ).delete()
```

---

## 12. Frontend Architecture

### Folder Structure

```
frontend/src/
├── app/(dashboard)/[workspace]/chat/
│   ├── page.tsx                       # Empty state + sidebar
│   └── [roomId]/page.tsx             # Chat room (refactored, lighter)
│
├── components/features/chat/          # NEW: chat-specific components
│   ├── chat-sidebar.tsx               # Room list (virtualized)
│   ├── chat-room-header.tsx           # Room header + right panel toggle
│   ├── chat-message-list.tsx          # Virtualized message list
│   ├── chat-message-item.tsx          # Single message (memo'd)
│   ├── chat-thread-panel.tsx          # Thread side panel
│   ├── chat-input.tsx                 # Auto-grow textarea with commands
│   ├── chat-floating-scroll.tsx       # Floating scroll-down button
│   ├── chat-reactions.tsx             # Reaction display + picker
│   ├── chat-right-panel.tsx           # Members, media, settings
│   └── chat-provider.tsx              # WebSocket provider + context
│
├── lib/
│   ├── stores/
│   │   ├── message-store.ts           # Map<roomId, Map<seq, Message>>
│   │   ├── presence-store.ts          # userId -> { status, lastActive }
│   │   ├── typing-store.ts            # roomId -> Set<userId>
│   │   ├── chat-store.ts             # activeRoom, unread, layout toggles
│   │   └── upload-store.ts           # File upload progress tracking
│   │
│   ├── ws/
│   │   └── chat-socket.ts            # Global WS client (refactored)
│   │
│   └── api/
│       ├── chat.ts                    # REST endpoints for chat v2
│       └── upload.ts                  # S3 presigned upload helpers
│
└── types/
    ├── chat.ts                        # Room, Message, etc. types
    └── ws.ts                          # WebSocket action/event types
```

---

## 13. Zustand Micro-Stores

### 13.1 `messageStore.ts`

```typescript
import { create } from 'zustand';

interface Message {
  message_id: string;
  seq: number;
  room_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  reply_to_seq: number | null;
  mention_user_ids: string[];
  attachment_urls: string[];
  is_edited: boolean;
  is_deleted?: boolean;
  created_at: string;
}

interface MessageStore {
  byRoom: Record<string, Map<number, Message>>;

  getMessages: (roomId: string) => Message[];
  getMessage: (roomId: string, seq: number) => Message | undefined;
  addMessage: (roomId: string, msg: Message) => void;
  addMessages: (roomId: string, msgs: Message[]) => void;
  updateContent: (roomId: string, seq: number, content: string) => void;
  markDeleted: (roomId: string, seq: number) => void;
  clearRoom: (roomId: string) => void;
}

export const useMessageStore = create<MessageStore>((set, get) => ({
  byRoom: {},

  getMessages: (roomId) => {
    const map = get().byRoom[roomId];
    if (!map) return [];
    return Array.from(map.values())
      .filter(m => !m.is_deleted || m.is_edited)
      .sort((a, b) => a.seq - b.seq);
  },

  getMessage: (roomId, seq) => get().byRoom[roomId]?.get(seq),

  addMessage: (roomId, msg) => {
    set((state) => {
      const map = new Map(state.byRoom[roomId] ?? []);
      if (map.has(msg.seq)) return state;
      map.set(msg.seq, msg);
      return { byRoom: { ...state.byRoom, [roomId]: map } };
    });
  },

  addMessages: (roomId, msgs) => {
    set((state) => {
      const map = new Map(state.byRoom[roomId] ?? []);
      for (const msg of msgs) {
        if (!map.has(msg.seq)) map.set(msg.seq, msg);
      }
      return { byRoom: { ...state.byRoom, [roomId]: map } };
    });
  },

  updateContent: (roomId, seq, content) => {
    set((state) => {
      const map = state.byRoom[roomId];
      if (!map) return state;
      const msg = map.get(seq);
      if (!msg) return state;
      const next = new Map(map);
      next.set(seq, { ...msg, content, is_edited: true });
      return { byRoom: { ...state.byRoom, [roomId]: next } };
    });
  },

  markDeleted: (roomId, seq) => {
    set((state) => {
      const map = state.byRoom[roomId];
      if (!map) return state;
      const msg = map.get(seq);
      if (!msg) return state;
      const next = new Map(map);
      next.set(seq, { ...msg, content: '[deleted]', is_deleted: true });
      return { byRoom: { ...state.byRoom, [roomId]: next } };
    });
  },

  clearRoom: (roomId) => {
    set((state) => {
      const next = { ...state.byRoom };
      delete next[roomId];
      return { byRoom: next };
    });
  },
}));
```

### 13.2 `presenceStore.ts`

```typescript
import { create } from 'zustand';

type PresenceStatus = 'ONLINE' | 'AWAY' | 'DND' | 'OFFLINE';

interface PresenceEntry {
  status: PresenceStatus;
  lastActive: number;
}

interface PresenceStore {
  byUserId: Record<string, PresenceEntry>;
  setStatus: (userId: string, status: PresenceStatus) => void;
  getStatus: (userId: string) => PresenceStatus;
}

export const usePresenceStore = create<PresenceStore>((set, get) => ({
  byUserId: {},
  setStatus: (userId, status) => {
    set((s) => ({
      byUserId: { ...s.byUserId, [userId]: { status, lastActive: Date.now() } },
    }));
  },
  getStatus: (userId) => get().byUserId[userId]?.status ?? 'OFFLINE',
}));
```

### 13.3 `typingStore.ts`

```typescript
import { create } from 'zustand';

interface TypingStore {
  byRoom: Record<string, Set<string>>;
  setTyping: (roomId: string, userId: string, isTyping: boolean) => void;
  getTypingUsers: (roomId: string) => string[];
}

export const useTypingStore = create<TypingStore>((set, get) => ({
  byRoom: {},
  setTyping: (roomId, userId, isTyping) => {
    set((s) => {
      const next = new Set(s.byRoom[roomId] ?? []);
      isTyping ? next.add(userId) : next.delete(userId);
      return { byRoom: { ...s.byRoom, [roomId]: next } };
    });
  },
  getTypingUsers: (roomId) => Array.from(get().byRoom[roomId] ?? []),
}));
```

### 13.4 `chatStore.ts` (Refactored)

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UnreadBadge {
  count: number;
  lastMsgSeq: number;
}

interface ChatStore {
  activeRoomId: string | null;
  sidebarOpen: boolean;
  rightPanelOpen: boolean;
  threadParentSeq: number | null;  // seq of parent message for thread panel
  unreadByRoom: Record<string, UnreadBadge>;

  setActiveRoom: (id: string | null) => void;
  toggleSidebar: () => void;
  toggleRightPanel: () => void;
  openThread: (parentSeq: number) => void;
  closeThread: () => void;
  incrementUnread: (roomId: string, seq: number) => void;
  clearUnread: (roomId: string) => void;
  totalUnread: () => number;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      activeRoomId: null,
      sidebarOpen: true,
      rightPanelOpen: false,
      threadParentSeq: null,
      unreadByRoom: {},

      setActiveRoom: (id) => set({ activeRoomId: id, threadParentSeq: null }),
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
      openThread: (seq) => set({ threadParentSeq: seq }),
      closeThread: () => set({ threadParentSeq: null }),

      incrementUnread: (roomId, seq) => {
        set((s) => {
          const prev = s.unreadByRoom[roomId];
          return {
            unreadByRoom: {
              ...s.unreadByRoom,
              [roomId]: { count: (prev?.count ?? 0) + 1, lastMsgSeq: seq },
            },
          };
        });
      },

      clearUnread: (roomId) => {
        set((s) => {
          const next = { ...s.unreadByRoom };
          delete next[roomId];
          return { unreadByRoom: next };
        });
      },

      totalUnread: () =>
        Object.values(get().unreadByRoom).reduce((a, b) => a + b.count, 0),
    }),
    {
      name: 'kraivor-chat-store',
      partialize: (s) => ({ unreadByRoom: s.unreadByRoom }),
    }
  )
);
```

### 13.5 `uploadStore.ts`

```typescript
import { create } from 'zustand';

interface UploadEntry {
  fileId: string;
  fileName: string;
  progress: number;
  status: 'uploading' | 'complete' | 'error';
  url?: string;
}

interface UploadStore {
  uploads: Record<string, UploadEntry>;
  startUpload: (fileId: string, fileName: string) => void;
  updateProgress: (fileId: string, progress: number) => void;
  completeUpload: (fileId: string, url: string) => void;
  failUpload: (fileId: string) => void;
  clearUpload: (fileId: string) => void;
}

export const useUploadStore = create<UploadStore>((set) => ({
  uploads: {},
  startUpload: (fileId, fileName) => {
    set((s) => ({
      uploads: { ...s.uploads, [fileId]: { fileId, fileName, progress: 0, status: 'uploading' } },
    }));
  },
  updateProgress: (fileId, progress) => {
    set((s) => {
      const e = s.uploads[fileId];
      return e ? { uploads: { ...s.uploads, [fileId]: { ...e, progress } } } : s;
    });
  },
  completeUpload: (fileId, url) => {
    set((s) => {
      const e = s.uploads[fileId];
      return e ? { uploads: { ...s.uploads, [fileId]: { ...e, progress: 100, status: 'complete', url } } } : s;
    });
  },
  failUpload: (fileId) => {
    set((s) => {
      const e = s.uploads[fileId];
      return e ? { uploads: { ...s.uploads, [fileId]: { ...e, status: 'error' } } } : s;
    });
  },
  clearUpload: (fileId) => {
    set((s) => {
      const next = { ...s.uploads };
      delete next[fileId];
      return { uploads: next };
    });
  },
}));
```

---

## 14. UI/UX Specifications

### 14.1 Message Area

- User messages aligned **right** (`ml-auto`), others **left**
- Group messages within **5-minute window** from same sender (Telegram style) — omit avatar and name header
- **Unread separation banner** — "New messages" divider when `seq` crosses `last_read_seq`
- Hover context menu — edit (own), delete (own), pin, reply, react
- Right-click context menu (future)

### 14.2 Auto-Grow Textarea

```tsx
<textarea
  value={input}
  onChange={handleChange}
  onKeyDown={handleKeyDown}
  rows={1}
  className="w-full bg-transparent resize-none px-3 py-2.5
             max-h-60 overflow-y-auto
             text-[14px] text-text-primary
             placeholder:text-text-tertiary
             focus:outline-none"
  placeholder={`Message #${room.name}`}
/>
```

- Auto-grows via `rows` calculation: `Math.min(lineCount, 15)` with `max-h-60`
- Supports: `/ai` prompt, `/repo file:path`, `@mention` autocomplete
- Drag-and-drop files → `uploadStore` → S3 presigned → append URL to textarea
- Paste image → same upload flow

### 14.3 Floating Scroll Button

```tsx
'use client';

import { useEffect, useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface FloatingScrollProps {
  containerRef: React.RefObject<HTMLDivElement | null>;
  onScrollDown: () => void;
}

export function FloatingScrollButton({ containerRef, onScrollDown }: FloatingScrollProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handler = () => {
      const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150;
      setVisible(!nearBottom);
    };
    el.addEventListener('scroll', handler, { passive: true });
    return () => el.removeEventListener('scroll', handler);
  }, [containerRef]);

  if (!visible) return null;

  return (
    <button
      onClick={() => {
        onScrollDown();
        setVisible(false);
      }}
      className="absolute bottom-4 right-6 z-20
                 w-10 h-10 rounded-full
                 bg-krait-surface3/80 backdrop-blur-md
                 border border-krait-borderHi
                 shadow-lg
                 flex items-center justify-center
                 hover:bg-krait-surface3
                 transition-all duration-200"
    >
      <ChevronDown className="w-4 h-4 text-text-primary" />
    </button>
  );
}
```

### 14.4 Thread Side Panel

- Triggered by clicking a message's reply icon or `useChatStore.openThread(seq)`
- Right-side panel (or slide-over on mobile) showing only thread replies
- Query: `DynamoDB Query(begins_with(sort_key, "THREAD#{seq:020d}#"))`
- Input box at bottom of panel for thread reply

### 14.5 Right Panel (Info Panel)

- Toggled by clicking room header
- Tabs:
  - **Members** — grouped by highest role priority, colored by role color
  - **Media** — grid of shared images/files from `attachment_urls`
  - **Pinned** — pinned messages list
  - **Settings** — permission-locked admin controls (room name, topic, roles)

---

## 15. Migration Strategy

### Deprecation Plan

| Phase | Status |
|-------|--------|
| Old chat remains fully functional | ✅ Now |
| New chat code behind feature flag (`CHAT_V2_ENABLED`) | Phase 1 |
| Feature flag default-off; opt-in via URL param `?chat=v2` | Phase 2 |
| Default-on, old chat still accessible via `?chat=v1` | Phase 3 |
| Old code removed | Phase 4 |

### Data Migration

**Start fresh** — no migration of existing messages. DynamoDB tables are separate (new table name: `kraivor-chat-v2`). Legacy `kraivor-chat-messages` table is left untouched and will be dropped after Phase 4.

---

## 16. File Map

### New Files to Create

| Path | Role |
|------|------|
| `services/core/apps/chat/models.py` | New Room, RoomMember, Role, RoomMemberRole, PinnedMessage, Draft, ScheduledMessage, RoomInvite |
| `services/core/apps/chat/dynamodb/repository.py` | ChatMessageRepository with single-table design |
| `services/core/apps/chat/dynamodb/__init__.py` | Package init |
| `services/core/apps/chat/consumers.py` | Refactored ChatConsumer (global WS, seq protocol) |
| `services/core/apps/chat/signals.py` | Workspace → TeamGroup auto-provision signals |
| `services/core/apps/chat/views/uploads.py` | S3 presigned upload endpoint |
| `services/core/apps/chat/urls.py` | Updated URL routing |
| `frontend/src/components/features/chat/chat-message-list.tsx` | Virtualized message list |
| `frontend/src/components/features/chat/chat-message-item.tsx` | Single message (memo'd) |
| `frontend/src/components/features/chat/chat-input.tsx` | Auto-grow textarea |
| `frontend/src/components/features/chat/chat-floating-scroll.tsx` | Floating scroll button |
| `frontend/src/components/features/chat/chat-thread-panel.tsx` | Thread side panel |
| `frontend/src/components/features/chat/chat-right-panel.tsx` | Members, media, settings |
| `frontend/src/components/features/chat/chat-sidebar.tsx` | Virtualized room list |
| `frontend/src/components/features/chat/chat-provider.tsx` | WS provider + context |
| `frontend/src/lib/stores/message-store.ts` | Map-based O(1) message store |
| `frontend/src/lib/stores/presence-store.ts` | Presence micro-store |
| `frontend/src/lib/stores/typing-store.ts` | Typing micro-store |
| `frontend/src/lib/stores/upload-store.ts` | Upload progress store |
| `frontend/src/lib/ws/chat-socket-v2.ts` | Refactored WS client |
| `frontend/src/lib/api/chat-v2.ts` | Updated REST endpoints |
| `frontend/src/types/chat.ts` | Chat-specific TypeScript types |

---

## 17. Implementation Phases

### Phase 1 — Backend Foundation (Week 1–2)

| Task | Files |
|------|-------|
| PostgreSQL models | `models.py` — Room, RoomMember, Role, RoomMemberRole |
| DynamoDB repository | `dynamodb/repository.py` — all write/query operations |
| Seq counter implementation | `ChatMessageRepository.allocate_seq()` + `init_counter()` |
| Migration + `makemigrations` | Auto-generated |

### Phase 2 — Real-Time Layer (Week 2–3)

| Task | Files |
|------|-------|
| Refactored WebSocket consumer | `consumers.py` — global connection, all handlers |
| SUBSCRIBE/SYNC/SEND protocol | Consumer methods for each action |
| Typing throttle + presence | Redis-backed cooldown, presence group broadcasts |
| WS routing update | `routing.py` — new URL pattern |

### Phase 3 — Signal & Auto-Provisioning (Week 3)

| Task | Files |
|------|-------|
| Workspace → TeamGroup signal | `signals.py` — `provision_team_group`, `add_to_team_group`, `remove_from_team_group` |
| WorkspaceMember sync | Signal handlers for join/leave |
| Workspace delete → archive | Soft-delete cascade |

### Phase 4 — Frontend Stores (Week 3–4)

| Task | Files |
|------|-------|
| messageStore | `lib/stores/message-store.ts` |
| presenceStore | `lib/stores/presence-store.ts` |
| typingStore | `lib/stores/typing-store.ts` |
| chatStore refactor | `lib/stores/chat-store.ts` |
| uploadStore | `lib/stores/upload-store.ts` |

### Phase 5 — Frontend UI (Week 4–6)

| Task | Files |
|------|-------|
| WS client refactor | `lib/ws/chat-socket-v2.ts` |
| Virtualized message list | `components/features/chat/chat-message-list.tsx` |
| Chat message item | `components/features/chat/chat-message-item.tsx` |
| Auto-grow input | `components/features/chat/chat-input.tsx` |
| Floating scroll button | `components/features/chat/chat-floating-scroll.tsx` |
| Thread panel | `components/features/chat/chat-thread-panel.tsx` |
| Right panel | `components/features/chat/chat-right-panel.tsx` |
| Sidebar virtualization | `components/features/chat/chat-sidebar.tsx` |
| WS provider | `components/features/chat/chat-provider.tsx` |

### Phase 6 — Integration & Testing (Week 6–7)

| Task | Description |
|------|-------------|
| Feature flag wiring | `CHAT_V2_ENABLED` setting + `?chat=v2` param |
| Room page refactor | Wire new components into `[roomId]/page.tsx` |
| E2E testing | Send/receive/thread/reaction/presence/connection |
| Performance testing | 10k rooms, 100k messages, low-end hardware |

### Phase 7 — Deprecation (Week 8)

| Task | Description |
|------|-------------|
| Default-on | `CHAT_V2_ENABLED = True` |
| Old code removed | Delete old consumers, views, components |
| Old DynamoDB table dropped | After confirmation of zero usage |
| This doc archived | Mark implementation complete |
