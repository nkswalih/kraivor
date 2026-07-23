# Kraivor Chat Service — Production Documentation

> **Document Version:** 1.0  
> **Last Updated:** 2026-07-09  
> **Service:** Core Service — Chat (Workspace Messaging)  
> **Classification:** Internal — Architecture

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Data Model](#3-data-model)
4. [Storage Strategy](#4-storage-strategy)
5. [REST API Reference](#5-rest-api-reference)
6. [WebSocket Protocol](#6-websocket-protocol)
7. [Complete Message Workflow](#7-complete-message-workflow)
8. [Room Management Workflow](#8-room-management-workflow)
9. [Unread Tracking](#9-unread-tracking)
10. [Presence System](#10-presence-system)
11. [Frontend State Architecture](#11-frontend-state-architecture)
12. [Async Processing](#12-async-processing)
13. [Key Decisions & Rationale](#13-key-decisions--rationale)
14. [Folder Structure](#14-folder-structure)
15. [File Reference](#15-file-reference)
16. [Sequence Diagrams](#16-sequence-diagrams)
17. [Edge Cases & Failure Modes](#17-edge-cases--failure-modes)

---

## 1. Introduction

### What the Chat Service Is

The Chat Service powers **human-to-human real-time messaging** within Kraivor workspaces. It supports channel-based group chat (public/private channels) and direct messages (DMs) between users. This is distinct from the AI Chat subsystem, which handles assistant conversations.

### Key Characteristics

| Attribute | Detail |
|-----------|--------|
| **Real-time** | WebSocket via Django Channels (layered on Redis channel layer) |
| **Persistence** | Dual-store: PostgreSQL (metadata) + DynamoDB (messages) |
| **Async writes** | Celery task for DynamoDB persistence |
| **Presence** | Redis SET per room + user-level keys with TTL |
| **Unread tracking** | Server-side via `last_read_message_count` on participant row |
| **Cursors** | DynamoDB cursor-based pagination for message history |
| **Soft deletes** | Messages are soft-deleted by setting `deleted_at` timestamp |

### Constraints & Assumptions

- Messages are eventually consistent (DynamoDB write is async via Celery)
- Room membership is managed server-side; only participants can read/send
- No message-level access control beyond room membership
- Search is case-sensitive, uses DynamoDB `contains` filter (no full-text index)

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                        │
│                                                                   │
│  ┌───────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ ChatRoomPage  │  │ ChannelSide  │  │  ChatSocket           │  │
│  │ (message list, │  │ bar (room    │  │  (WebSocket client    │  │
│  │  send, edit,   │  │ list, crud)  │  │   heartbeat, reconnect│  │
│  │  delete, WS)   │  │              │  │   exponential backoff)│  │
│  └───────┬───────┘  └──────┬───────┘  └──────────┬────────────┘  │
│          │                 │                      │               │
│  ┌───────┴─────────────────┴──────────────────────┴────────────┐  │
│  │              Zustand Stores (chat-store.ts)                  │  │
│  │  rooms[] | messagesByRoom{} | unreadCounts | typingByRoom   │  │
│  │  localStorage persistence for unread counts                 │  │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬───────────────────────────────────────┘
                           │
           ┌───────────────┼─────────────────────┐
           │               │                     │
      REST API        WebSocket               REST
      (history,       (real-time              (room mgmt,
       search)         messages)               CRUD)
           │               │                     │
           ▼               ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    CORE SERVICE (Django)                     │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────────────────┐     │
│  │  DRF Views        │  │  Django Channels Consumers  │     │
│  │  · RoomListCreate │  │  · ChatConsumer             │     │
│  │  · RoomDetail     │  │  · NotificationConsumer     │     │
│  │  · DMCreate       │  │  · PresenceConsumer         │     │
│  │  · MessageListSend│  └──────────┬───────────────────┘     │
│  │  · MessageDetail  │             │                         │
│  │  · MessageSearch  │             │                         │
│  └────────┬──────────┘             │                         │
│           │                        │                         │
│           ▼                        ▼                         │
│  ┌──────────────────────────────────────────────┐            │
│  │         Service Layer                         │            │
│  │  ChatRoomService · ChatMessageService         │            │
│  └──────┬───────────────────────────────────────┘            │
│         │                                                     │
│    ┌────┴──────────────┐         ┌────────────────────────┐  │
│    │  PostgreSQL       │         │  DynamoDB              │  │
│    │  · chat_rooms     │         │  · kraivor-chat-       │  │
│    │  · chat_room_     │         │    messages table      │  │
│    │    participants   │         │  (room_id PK, msg_id   │  │
│    │  (metadata,       │         │   SK, cursor-paginated)│  │
│    │   unread)         │         │                         │  │
│    └───────────────────┘         └────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Celery Workers                                       │    │
│  │  · persist_to_dynamodb (message persistence)          │    │
│  │  · trigger_ai_response (when @ai mentioned)           │    │
│  │  · dispatch_notification (on @mentions)               │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Redis                                                │    │
│  │  · Channel layer (Django Channels pub/sub)            │    │
│  │  · Presence tracking (presence:room:{id} SET)        │    │
│  │  · User heartbeat (presence:user:{id} key)           │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Data Model

### 3.1 PostgreSQL — Chat Rooms

**Table: `chat_rooms`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `workspace_id` | FK → workspaces | Parent workspace |
| `name` | VARCHAR(255) | Display name |
| `room_type` | VARCHAR(20) | `workspace` \| `group` \| `dm` \| `ai` |
| `topic` | TEXT | Room description |
| `created_by` | UUID | User who created it |
| `is_active` | BOOLEAN | Soft-delete flag |
| `last_message_at` | DATETIME | Timestamp of most recent message |
| `last_message_content` | TEXT | Preview of last message |
| `last_message_sender_name` | VARCHAR(255) | Sender of last message |
| `message_count` | INTEGER | Total messages sent |
| `created_at` | DATETIME | Auto-set |
| `updated_at` | DATETIME | Auto-updated |

**Indexes:**
- `(workspace_id, room_type)` — filter channels, DMs per workspace
- `(workspace_id, created_by)` — user's rooms lookup
- `(is_active, -last_message_at)` — active rooms sorted by recent

**Table: `chat_room_participants`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `room_id` | FK → chat_rooms | Room membership |
| `user_id` | UUID | Member user |
| `joined_at` | DATETIME | When they joined |
| `left_at` | DATETIME | Null if still member |
| `last_read_message_count` | INTEGER | For unread tracking |

**Constraints:** Unique `(room_id, user_id)`, indexes on `(user_id, room)`.

### 3.2 DynamoDB — Chat Messages

**Table: `kraivor-chat-messages`**

| Attribute | Type | Key | Description |
|-----------|------|-----|-------------|
| `room_id` | String | Partition key | Room the message belongs to |
| `message_id` | String | Sort key | UUID v4 |
| `sender_id` | String | — | User ID |
| `sender_name` | String | — | Display name at send time |
| `content` | String | — | HTML-escaped text |
| `content_type` | String | — | `text`, `image`, etc. |
| `reply_to` | String | — | Parent message ID or empty |
| `mentions` | List of String | — | Mentioned user IDs |
| `attachment_url` | String | — | File attachment URL or empty |
| `created_at` | String | — | ISO 8601 |
| `edited_at` | String | — | Empty if never edited |
| `deleted_at` | String | — | Empty if not deleted |

**Query pattern:** `room_id = :room_id` with `ScanIndexForward: false` (reverse chronological), `Limit: N`, optional `ExclusiveStartKey` for cursor pagination.

**Search:** Uses `FilterExpression: contains(content, :query) AND deleted_at = :empty` — note this is a full table scan within the partition (no GSI).

---

## 4. Storage Strategy

### Why Both PostgreSQL and DynamoDB?

| Concern | PostgreSQL | DynamoDB |
|---------|-----------|----------|
| Room metadata | ✅ Relational joins, foreign keys | ❌ No joins |
| Message history | ❌ Would bloat row count | ✅ Infinite scale, cheap writes |
| Unread tracking | ✅ Atomic counter increments | ❌ Eventual consistency issues |
| Presence | ❌ Ephemeral data | ❌ No TTL |
| Search | ✅ Full-text search capable | ⚠️ `contains` scan only |
| Cursor pagination | ⚠️ Offset-based (slow at scale) | ✅ Native cursor via `ExclusiveStartKey` |

### Trade-off: Eventual Consistency for Messages

Messages written via WebSocket are immediately broadcast to the room group, then asynchronously persisted to DynamoDB via Celery. This means:
- Other online users see the message immediately via WebSocket broadcast
- The message becomes queryable (history, search) only after the Celery task completes
- If the Celery task fails, the message is lost from history (but still seen in real-time)

The REST `POST` endpoint bypasses this — it writes directly to DynamoDB synchronously before returning.

---

## 5. REST API Reference

All endpoints are prefixed with `/workspaces/{workspace_pk}/chat/`. Authentication: JWT in `Authorization` header.

### Room Endpoints

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `/rooms/` | List rooms user can see (channels + their DMs) | 200 |
| `POST` | `/rooms/` | Create channel/group room | 201, 400 |
| `GET` | `/rooms/{id}/` | Get room detail | 200, 404 |
| `PATCH` | `/rooms/{id}/` | Update name/topic | 200, 400, 404 |
| `DELETE` | `/rooms/{id}/` | Archive room (soft-delete) | 200, 404 |
| `POST` | `/dm/` | Create or find existing DM with target user | 200 |

**List rooms** returns rooms sorted by `last_message_at DESC, name ASC`. Non-DM rooms visible to workspace members. DM rooms only visible if user is a participant.

**Create DM** looks for an existing room where both participants exist. If found, returns it (200). If not, creates a new one (201).

### Message Endpoints

| Method | Path | Description | Status Codes |
|--------|------|-------------|--------------|
| `GET` | `/rooms/{id}/messages/` | Cursor-paginated message list | 200, 400 |
| `POST` | `/rooms/{id}/messages/` | Send message (sync write) | 201, 400 |
| `GET` | `/rooms/{id}/messages/{msg_id}/` | Get single message | 200, 404, 503 |
| `PATCH` | `/rooms/{id}/messages/{msg_id}/` | Edit own message | 200, 400, 404 |
| `DELETE` | `/rooms/{id}/messages/{msg_id}/` | Soft-delete message | 200, 404, 503 |
| `GET` | `/rooms/{id}/messages/search/?q=` | Search messages (min 2 chars) | 200, 400, 503 |

**Pagination:** Accepts `limit` (default 50, max 200) and `start_key` (JSON object from previous response's `next_start_key`). Returns `{ results: [], has_next: bool, next_start_key: string | null }`.

**Send (REST):** Writes to DynamoDB synchronously, updates `last_message_*` fields on room, fires `message_sent` signal.

---

## 6. WebSocket Protocol

### Connection

```
ws://{host}/ws/chat/{room_id}/?token={jwt}
```

Authentication via query param token. Closes with code `4001` if no valid user.

### Client → Server Actions

All messages are JSON with an `action` field:

```typescript
type WsClientAction =
  | { action: 'message';        content: string; content_type?: string; mentions?: string[]; reply_to?: string }
  | { action: 'typing.start' }
  | { action: 'typing.stop' }
  | { action: 'mark_read';     message_id: string }
  | { action: 'delete';        message_id: string }
  | { action: 'heartbeat' }
```

### Server → Client Events

```typescript
type WsServerEvent =
  | { type: 'message';      message_id: string; sender_id: string; sender_name: string; content: string; content_type: string; reply_to: string; mentions: string[]; created_at: string }
  | { type: 'typing.start' | 'typing.stop'; user_id: string; user_name: string }
  | { type: 'presence';     user_id: string; status: 'online' | 'offline' }
```

### Protocol Notes

- **No ACK for sends**: The sender does not receive their own message via WebSocket. The REST send path (`POST .../messages/`) is used for the sender's UI to add the message optimistically.
- **Heartbeat**: Sent every 40 seconds by the client to keep the connection alive. The server's `ChatConsumer._handle_message` dispatches based on action — `heartbeat` is not explicitly handled (it falls through the unknown action handler). Presence refresh happens via the `PresenceConsumer` WebSocket instead.
- **Reconnection**: `ChatSocket` implements exponential backoff with jitter (1s–30s base, 2x multiplier, ±50% jitter), up to 10 retries. Disconnection codes `4001/4002/4003` are treated as auth errors and do not trigger reconnection.

---

## 7. Complete Message Workflow

### 7.1 Send Message (REST path — used by sender)

```
User types + hits Enter
  │
  ▼
ChatRoomPage.handleSend()
  │  sendMutation.mutate(content)
  │
  ▼
chatEndpoints.sendMessage(workspaceId, roomId, { content })
  │  POST /workspaces/{pk}/chat/rooms/{pk}/messages/
  │
  ▼
MessageListSendView.post()  [views/messages.py:142]
  │
  ├─ Validates via SendMessageSerializer
  ├─ Generates UUID message_id
  ├─ ChatMessageService.send_message_via_api()
  │   ├─ DynamoDB.put_message()        ← synchronous write
  │   ├─ ChatRoomService.update_last_message()  ← PostgreSQL
  │   └─ ChatRoomService.increment_message_count()  ← PostgreSQL
  ├─ Fires message_sent Signal
  └─ Returns MessageSerializer (201)
  │
  ▼
sendMutation.onSuccess → addMessage(roomId, msg) → Zustand store
  │
  ▼
React re-render → message appears in list, auto-scroll to bottom
```

### 7.2 Send Message (WebSocket path — real-time broadcast)

```
User types + hits Enter
  │
  ▼
ChatSocket.send({ action: 'message', content: '...' })
  │  ws://host/ws/chat/{room_id}/?token={jwt}
  │
  ▼
ChatConsumer.receive() → _handle_message()  [consumers.py:133]
  │
  ├─ 1. HTML-escape content
  │
  ├─ 2. _update_last_message()  ← PostgreSQL (sync)
  │      ├─ chat_rooms.last_message_content = content
  │      ├─ chat_rooms.last_message_sender_name = sender
  │      ├─ chat_rooms.last_message_at = now
  │      └─ chat_rooms.message_count += 1
  │
  ├─ 3. channel_layer.group_send('chat_{room_id}', 'chat_message')
  │     └─ ALL other clients in the room receive via chat_message()
  │         └─ Zustand.addMessage(roomId, event) → re-render
  │
  ├─ 4. Celery: persist_to_dynamodb.delay()
  │     └─ Async write to DynamoDB (retry 3x, exponential backoff)
  │
  ├─ 5. If "@ai" or "assistant" in content:
  │     └─ Celery: trigger_ai_response.delay()
  │
  └─ 6. For each mentioned user_id != sender:
        └─ Celery: dispatch_notification_task.delay()
```

### 7.3 Receiving Messages

**Sender's perspective:**
- REST `POST` response populates the message in Zustand via `onSuccess`
- Message appears immediately without waiting for WebSocket round-trip

**Other clients' perspective:**
- `ChatConsumer.chat_message()` sends JSON to all WebSocket connections in the room group
- `ChatRoomPage.socket.onEvent` of type `'message'` → `addMessage(roomId, event)`
- Zustand deduplicates by `message_id`

**Late-joining / loading history:**
- `useQuery(['messages', workspaceId, roomId])` → `GET .../messages/?limit=50`
- Cursor-based pagination for infinite scroll up

### 7.4 Edit Message

```
User clicks Edit → inline input appears
  │  editMut.mutate({ messageId, content })
  │
  ▼
PATCH /workspaces/{pk}/chat/rooms/{pk}/messages/{id}/
  │
  ▼
MessageDetailView.patch()  [views/messages.py:249]
  ├─ Validates sender owns message (sender_id check)
  ├─ DynamoDB: update_item(content=..., edited_at=now)
  └─ Returns updated MessageSerializer
  │
  ▼
editMutation.onSuccess → updateMessage(roomId, msg) → Zustand
  └─ Message re-renders with new content + "(edited)" badge
```

### 7.5 Delete Message

```
User clicks Delete → confirm dialog
  │  deleteMut.mutate(messageId)
  │
  ▼
DELETE /workspaces/{pk}/chat/rooms/{pk}/messages/{id}/
  │
  ▼
MessageDetailView.delete()  [views/messages.py:296]
  ├─ DynamoDB: update_item SET deleted_at = now (soft delete)
  └─ Returns { status: 'deleted' }
  │
  ▼
deleteMutation.onSuccess → removeMessage(roomId, messageId) → Zustand
  └─ Message removed from list

WebSocket path (for real-time deletion):
  ChatSocket.send({ action: 'delete', message_id })
  └─ ChatConsumer._handle_delete()
      ├─ DynamoDB: soft-delete
      └─ Broadcasts { type: 'message', deleted: true, message_id } to room
```

---

## 8. Room Management Workflow

### 8.1 Create Channel

```
ChannelSidebar → "Create Channel" dialog
  └─ POST /workspaces/{pk}/chat/rooms/ { name, room_type: 'group'|'workspace' }
      └─ ChatRoomService.create_room()
          ├─ INSERT chat_rooms
          ├─ INSERT chat_room_participants (for specified member IDs)
          └─ Returns ChatRoom
```

### 8.2 Create / Find DM

```
ChannelSidebar → click user → createDm
  └─ POST /workspaces/{pk}/chat/dm/ { target_user_id, target_user_name }
      └─ ChatRoomService.get_or_create_dm_room()
          ├─ Query: find room with both participants (cnt=2)
          ├─ If found → return existing (200)
          └─ If not → INSERT chat_room + INSERT 2 participants (201)
```

### 8.3 Archive Room

```
ChannelSidebar → Archive → confirm
  └─ DELETE /workspaces/{pk}/chat/rooms/{id}/
      └─ ChatRoomService.archive_room()
          └─ UPDATE chat_rooms SET is_active = False
```

**Note:** Archived rooms are filtered out of `list_rooms` and `get_room` queries. No messages are deleted.

### 8.4 Room Listing Logic

`ChatRoomService.list_rooms(workspace_id, user_id)`:

1. Fetch all active non-DM rooms (visible to workspace members)
2. Fetch DM room IDs where user is a participant
3. Fetch those DM rooms
4. Combine + sort by `last_message_at DESC, name ASC`
5. For DM rooms, attach `_participant_ids` (used for display names in sidebar)

---

## 9. Unread Tracking

### Server-Side Model

- `ChatRoom.message_count` = total messages ever sent in the room
- `ChatRoomParticipant.last_read_message_count` = value of `message_count` at last read
- **Unread count** = `room.message_count - participant.last_read_message_count`

### Mark as Read

Triggered on:
- WebSocket connection to a room (`ChatConsumer.connect()` calls `mark_room_read`)
- WebSocket `mark_read` action
- When `setCurrentRoom(roomId)` fires on the frontend

```python
def mark_room_read(room_id, user_id):
    count = ChatRoom.objects.get(id=room_id).message_count
    ChatRoomParticipant.objects.update_or_create(
        room_id=room_id, user_id=user_id,
        defaults={"last_read_message_count": count}
    )
```

### Frontend State

Two layers of unread tracking:

1. **Server-synced**: `ChatRoom.unread_count` returned from room list API → `syncUnreadFromRooms()` updates Zustand + localStorage
2. **Client-side increment**: When a WebSocket message arrives for a non-active room, `addMessage()` calls `incrementUnread(roomId)` which bumps the local counter and persists to localStorage

**localStorage key:** `chat_unread_v2` — stores `{ unreadCounts: Record<roomId, number>, lastReadAt: Record<roomId, timestamp> }`. This survives page refreshes.

**Edge case:** If localStorage gets out of sync with the server, the next room list fetch via `syncUnreadFromRooms()` overwrites with server values.

---

## 10. Presence System

### Room-Level Presence (via ChatConsumer)

| Event | Consumer Action |
|-------|----------------|
| WebSocket connect | `SADD presence:room:{room_id} {user_id}` → broadcast `presence: online` |
| WebSocket disconnect | `SREM presence:room:{room_id} {user_id}` → broadcast `presence: offline` |
| TTL | 120 seconds on the SET (refreshed by heartbeat?) |

Currently the `ChatConsumer` does **not** refresh presence on heartbeat; room presence is tied to the WebSocket connection lifecycle. If the connection drops without clean disconnect (e.g., network loss), the user stays "online" for up to 120s until Redis expires the key.

### Global User Presence (via PresenceConsumer)

- `PresenceConsumer.connect()`: `SETEX presence:user:{user_id} 60 "online"`
- `PresenceConsumer.disconnect()`: `DEL presence:user:{user_id}`
- `PresenceConsumer.receive({ action: 'heartbeat' })`: `EXPIRE presence:user:{user_id} 60`

### Frontend Consumption

`ChatRoomPage` maintains `onlineUserIds: Set<string>` updated from `presence` events. Passed to `MembersPanel` to show green indicators.

---

## 11. Frontend State Architecture

### Zustand Store (`chat-store.ts`)

| State Key | Type | Persisted | Description |
|-----------|------|-----------|-------------|
| `rooms` | `ChatRoom[]` | No | Full room list from API |
| `messagesByRoom` | `Record<roomId, ChatMessage[]>` | No | In-memory message cache |
| `typingByRoom` | `Record<roomId, TypingUser[]>` | No | Active typing indicators |
| `nextKeyByRoom` | `Record<roomId, string\|null>` | No | Pagination cursors |
| `unreadCounts` | `Record<roomId, number>` | Yes (localStorage) | Badge counts |
| `lastReadAt` | `Record<roomId, number>` | Yes (localStorage) | Timestamp of last read |
| `currentRoomId` | `string\|null` | No | Currently active room |

### State Flow

```
💬 New message arrives (WebSocket or REST)
  → addMessage(roomId, msg)
    → dedupe by message_id
    → append to messagesByRoom[roomId]
    → if roomId ≠ currentRoomId → incrementUnread(roomId)
      → persist to localStorage

📜 Page loads with roomId
  → setCurrentRoom(roomId)
    → clearUnread(roomId) → remove from localStorage
  → useQuery(['messages', ...]) → GET .../messages/
    → prependMessages(roomId, results)
    → setNextKey(roomId, next_start_key)

⬆️ Scroll to top
  → handleScroll → loadOlder()
    → GET .../messages/?start_key={nextKey}
    → prependMessages (deduped merge)
```

### Deduplication Strategy

Both `addMessage` and `prependMessages` filter out messages whose `message_id` already exists in the array. This prevents duplicates when:
- The sender receives confirmation via both REST and their own WebSocket broadcast
- Pagination overlaps occur at cursor boundaries

---

## 12. Async Processing

### Celery Tasks

| Task | Queue | Retries | Trigger | Description |
|------|-------|---------|---------|-------------|
| `chat.persist_to_dynamodb` | `default` | 3 (10s delay, 2x backoff) | WebSocket `message` action | Write message to DynamoDB |
| `chat.trigger_ai_response` | `default` | 2 (30s delay) | Message contains "@ai"/"assistant" | HTTP call to AI service (placeholder) |
| Notifications | N/A | N/A | Message contains `@mentions` | Dispatched via separate `dispatch_notification` task |

### Celery Configuration

```python
# Key settings
task_acks_late = True     # Re-deliver on worker crash
task_reject_on_worker_lost = True
broker = Redis            # (same Redis as channel layer)
```

### Eventual Consistency Window

```
WebSocket message received at T+0
  ↓
Broadcast to room: T+1 (milliseconds)
  ↓
Celery task enqueued: T+2
  ↓
DynamoDB write: T+50ms to T+5s (depends on worker availability, queue depth)
```

During this window, the message is visible in real-time but not queryable via REST history or search.

---

## 13. Key Decisions & Rationale

### Decision 1: DynamoDB for Messages, PostgreSQL for Metadata

**Chosen:** Hybrid approach. Messages in DynamoDB; rooms, participants, unread tracking in PostgreSQL.

**Rationale:**
- Messages are fundamentally key-value (room → ordered list of messages), a natural fit for DynamoDB
- Rooms require relational queries (join workspace → rooms → participants), better suited to PostgreSQL
- Message volume can grow unboundedly without affecting room query performance
- DynamoDB provides cursor pagination natively (avoids offset-based pagination problems)

**Cost:** Each message sent via WebSocket requires one DynamoDB write unit + one PostgreSQL update (for last_message metadata) + one Celery task.

### Decision 2: Dual Send Paths (REST + WebSocket)

**Chosen:** Sender uses REST, others receive via WebSocket.

**Rationale:**
- Sender gets synchronous confirmation (message_id, server timestamp) for optimistic UI
- No need for WebSocket message ID acknowledgment protocol
- Other clients get real-time push without polling

**Downside:** If the REST send succeeds but the WebSocket broadcast for other clients fails, only the sender sees the message. This is mitigated by the DynamoDB persistence — other users will see it when they load history.

### Decision 3: Soft Deletes

**Chosen:** Messages are soft-deleted by setting `deleted_at` timestamp.

**Rationale:**
- Allows undo/restore operations in the future
- Prevents orphan references (reply_to pointing to deleted message)
- History queries filter by `deleted_at = ''`

### Decision 4: No Read Receipts / Delivery Confirmation

**Chosen:** Not implemented.

**Rationale:** Unread counts provide aggregate "read" state. Per-message read receipts would require significant write amplification (one DynamoDB update per recipient per message).

### Decision 5: HTML Escaping on Server

**Chosen:** Content is HTML-escaped server-side in `ChatConsumer.chat_message()` via `html.escape()`.

**Rationale:** Prevents XSS through message content. The content is rendered as-is on the frontend without sanitization.

---

## 14. Folder Structure

### Backend (Django)

```
services/core/apps/chat/
├── __init__.py
├── admin.py
├── apps.py
├── consumers.py              # ChatConsumer, NotificationConsumer, PresenceConsumer
├── dynamodb.py                # ChatMessageRepository (DynamoDB CRUD)
├── handlers.py                # Signal handlers
├── models.py                  # ChatRoom, ChatRoomParticipant ORM
├── permissions.py             # IsChatRoomMember
├── routing.py                 # WebSocket URL patterns
├── signals.py                 # message_sent Signal
├── tasks.py                   # Celery tasks
├── urls.py                    # REST URL patterns
├── management/
│   └── commands/
│       └── create_chat_table.py  # DynamoDB table creation script
├── migrations/                # Django migrations
├── serializers/
│   ├── __init__.py
│   ├── message_serializers.py
│   └── room_serializers.py
├── services/
│   ├── __init__.py
│   ├── message.py             # ChatMessageService
│   └── room.py                # ChatRoomService
└── views/
    ├── __init__.py
    ├── exceptions.py
    ├── messages.py            # MessageListSendView, MessageDetailView, MessageSearchView
    └── rooms.py               # RoomListCreateView, RoomDetailView, DMCreateView
```

### Frontend

```
frontend/src/
├── app/(dashboard)/[workspace]/chat/
│   ├── page.tsx                # Empty state + ChannelSidebar
│   └── [roomId]/page.tsx       # Main chat view (messages, send, edit, delete, WS)
├── components/features/
│   └── channel-sidebar.tsx     # Room list, create, rename, archive
├── lib/
│   ├── api/endpoints/chat.ts   # REST API client
│   ├── stores/chat-store.ts    # Zustand store (messages, rooms, unread, typing)
│   └── ws/chat-socket.ts       # WebSocket client
└── types/
    ├── api/index.ts            # ChatRoom, ChatMessage, SendMessagePayload types
    └── ws.ts                   # WsClientAction, WsServerEvent types
```

---

## 15. File Reference

| File | Lines | Role |
|------|-------|------|
| `services/core/apps/chat/consumers.py` | 372 | WebSocket consumers: message handling, broadcast, typing, presence, delete, mark-read |
| `services/core/apps/chat/dynamodb.py` | 270 | DynamoDB repository: put, get, query, update, delete, search, batch-get |
| `services/core/apps/chat/models.py` | 65 | ChatRoom + ChatRoomParticipant ORM models |
| `services/core/apps/chat/tasks.py` | 82 | Celery: persist_to_dynamodb, trigger_ai_response |
| `services/core/apps/chat/views/rooms.py` | 220 | Room REST endpoints (list, create, detail, update, archive, DM) |
| `services/core/apps/chat/views/messages.py` | 393 | Message REST endpoints (list, send, get, edit, delete, search) |
| `services/core/apps/chat/services/room.py` | 183 | ChatRoomService: CRUD, list, DM, unread |
| `services/core/apps/chat/services/message.py` | 103 | ChatMessageService: send, get, edit, delete, search |
| `services/core/apps/chat/routing.py` | 15 | WebSocket URL routing |
| `services/core/apps/chat/urls.py` | 43 | REST URL routing |
| `services/core/apps/chat/signals.py` | 3 | message_sent Signal definition |
| `frontend/src/app/(dashboard)/[workspace]/chat/[roomId]/page.tsx` | 480 | Full chat UI |
| `frontend/src/app/(dashboard)/[workspace]/chat/page.tsx` | 33 | Empty state |
| `frontend/src/components/features/channel-sidebar.tsx` | 282 | Room sidebar |
| `frontend/src/lib/stores/chat-store.ts` | 153 | Zustand state store |
| `frontend/src/lib/ws/chat-socket.ts` | 94 | WebSocket client |
| `frontend/src/lib/api/endpoints/chat.ts` | 66 | REST client |
| `frontend/src/types/ws.ts` | 42 | WebSocket types |

---

## 16. Sequence Diagrams

### 16.1 Send Message (Sender via REST)

```
Sender                 Frontend                Core API              PostgreSQL        DynamoDB
  │                       │                       │                     │                 │
  │  type message         │                       │                     │                 │
  │──────────────────────►│                       │                     │                 │
  │                       │                       │                     │                 │
  │                       │ POST /messages/       │                     │                 │
  │                       │──────────────────────►│                     │                 │
  │                       │                       │                     │                 │
  │                       │                       │ put_message() ──────│────────────────►│
  │                       │                       │◄────────────────────│─────────────────│
  │                       │                       │                     │                 │
  │                       │                       │ update_last_message()│                 │
  │                       │                       │────────────────────►│                 │
  │                       │                       │◄────────────────────│                 │
  │                       │                       │                     │                 │
  │                       │  201 { message }      │                     │                 │
  │                       │◄──────────────────────│                     │                 │
  │                       │                       │                     │                 │
  │                       │ addMessage(store)      │                     │                 │
  │                       │──────────────────────►│                     │                 │
  │                       │ (Zustand)             │                     │                 │
  │                       │                       │                     │                 │
  │  message appears      │                       │                     │                 │
  │◄──────────────────────│                       │                     │                 │
```

### 16.2 Real-Time Broadcast (Other Clients via WebSocket)

```
Sender WS              Core WS                Redis              Other Clients
  │                      │ (Channel Layer)       │                     │
  │                      │                       │                     │
  │ {action: 'message'}  │                       │                     │
  │─────────────────────►│                       │                     │
  │                      │                       │                     │
  │                      │ _update_last_message  │                     │
  │                      │───► PostgreSQL        │                     │
  │                      │                       │                     │
  │                      │ group_send() ────────►│                     │
  │                      │                       │                     │
  │                      │                       │ broadcast to group  │
  │                      │                       ├────────────────────►│
  │                      │                       │ {type:'message',...}│
  │                      │                       │                     │
  │                      │ Celery: persist       │                     │
  │                      │───► DynamoDB (async)  │                     │
  │                      │                       │                     │
  │                      │                       │   addMessage(store) │
  │                      │                       │◄────────────────────│
  │                      │                       │                     │
```

### 16.3 Message History Load (Late Joiner / Page Refresh)

```
User                    Frontend                  Core API              DynamoDB
  │                        │                          │                     │
  │ navigate to /chat/     │                          │                     │
  │──[roomId]─────────────►│                          │                     │
  │                        │                          │                     │
  │                        │ GET /rooms/{id}/          │                     │
  │                        │─────────────────────────►│                     │
  │                        │◄─────────────────────────│                     │
  │                        │   { room detail }        │                     │
  │                        │                          │                     │
  │                        │ GET /messages/?limit=50   │                     │
  │                        │─────────────────────────►│                     │
  │                        │                          │ query(room_id) ────►│
  │                        │                          │◄────────────────────│
  │                        │◄─────────────────────────│                     │
  │                        │   { results, has_next,   │                     │
  │                        │     next_start_key }     │                     │
  │                        │                          │                     │
  │                        │ prependMessages(store)    │                     │
  │                        │ setNextKey(store)         │                     │
  │                        │                          │                     │
  │  messages displayed    │                          │                     │
  │◄───────────────────────│                          │                     │
```

---

## 17. Edge Cases & Failure Modes

### 17.1 Network Disconnect During Send

| Path | Behavior |
|------|----------|
| REST send | Mutation fails → error toast, message not added |
| WebSocket send | Connection drop detected by `onclose` → reconnect with exponential backoff. Unsent messages are **lost** (no outbox pattern). |

**Mitigation:** None currently. A future improvement could implement a local outbox with retry.

### 17.2 DynamoDB Write Failure (Celery Task)

If `persist_to_dynamodb` fails after all retries:
- Message is lost from history (not queryable)
- Real-time recipients still have it in their local store (but lose it on refresh)
- Room's `last_message_*` fields in PostgreSQL remain updated (desync)

**Detection:** `persist_to_dynamodb` logs errors. No alerting or dead-letter queue currently configured.

### 17.3 Race: REST + WebSocket Duplicates

When sender's REST call returns a message, and the WebSocket broadcast reaches them before the REST response is processed:

| Sequence | Result |
|----------|--------|
| REST response → addMessage → WS message → addMessage (deduped) | ✅ Single message |
| WS message → addMessage → REST response → addMessage (deduped) | ✅ Single message |
| Both arrive via same event loop tick | ✅ Deduped by `message_id` |

The `addMessage` function checks `existing.some(m ⇒ m.message_id === msg.message_id)` before inserting.

### 17.4 Stale Presence Data

If the WebSocket disconnects without a clean close (e.g., browser crash):
- Redis `presence:room:{id}` membership persists for up to 120s (SET TTL)
- User appears "online" to others during this window

**Mitigation:** 120s TTL is a trade-off between responsiveness and accuracy. A shorter TTL would require more frequent heartbeats.

### 17.5 Concurrent Edits

No locking or versioning on message edits. Two users (the sender from different devices) could overwrite each other's edits. Last write wins.

### 17.6 Room Archive With Active Participants

Archiving a room does not disconnect participants. They continue to see the room until they navigate away or refresh. Subsequent `list_rooms` will not include the archived room, so it effectively disappears from the sidebar.

### 17.7 Large Messages

No server-enforced limit on message content length. The textarea also has no max length. Very large messages could:
- Exceed DynamoDB item size limit (400 KB)
- Cause memory pressure in WebSocket broadcast
- Break UI layout

---

## Appendix A: Future Improvements

| Improvement | Effort | Impact | Priority |
|-------------|--------|--------|----------|
| Message outbox (retry on WS disconnect) | Medium | Prevents message loss | High |
| DynamoDB GSI for full-text search | Medium | Better search performance | High |
| Read receipts via DynamoDB | High | Per-message read tracking | Low |
| Message reactions / emoji | Medium | User engagement | Medium |
| File attachments via S3 | Medium | Richer messaging | Medium |
| Dead-letter queue for failed tasks | Low | Operational reliability | Medium |
| Message content size limit | Low | Prevent abuse | Medium |
| Typing indicator timeouts | Low | Prevent stale indicators | Low |

## Appendix B: Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `DYNAMODB_CHAT_TABLE` | `kraivor-chat-messages` | DynamoDB table name |
| `CHAT_MESSAGE_LIMIT_MAX` | `200` | Max messages per page |
| `CHAT_MESSAGE_LIMIT_DEFAULT` | `50` | Default messages per page |
| `PRESENCE_ROOM_TTL` | `120` | Room presence set TTL (seconds) |
| `PRESENCE_USER_TTL` | `60` | User presence key TTL (seconds) |
| `WS_HEARTBEAT_INTERVAL` | `40` | Frontend heartbeat interval (seconds) |
| `WS_RECONNECT_MAX` | `10` | Maximum reconnection attempts |
| `WS_RECONNECT_BASE` | `1000` | Initial reconnect delay (ms) |
| `WS_RECONNECT_MAX_DELAY` | `30000` | Maximum reconnect delay (ms) |
