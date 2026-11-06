# Kraivor Chat v2 — System Design

> **Document Version:** 1.0  
> **Last Updated:** 2026-07-09  
> **Service:** Core Service — Chat Rebuild  
> **Status:** Approved — In Development  
> **Classification:** Internal — Design

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Data Store Decision Matrix](#2-data-store-decision-matrix)
3. [PostgreSQL Schema Design](#3-postgresql-schema-design)
4. [DynamoDB Single-Table Design](#4-dynamodb-single-table-design)
5. [Atomic Seq Counter](#5-atomic-seq-counter)
6. [Redis Key Design](#6-redis-key-design)
7. [S3 Upload Flow](#7-s3-upload-flow)
8. [Data Flow Diagrams](#8-data-flow-diagrams)
9. [Consistency Model](#9-consistency-model)
10. [Scalability Design](#10-scalability-design)
11. [Security Design](#11-security-design)
12. [Failure Modes](#12-failure-modes)
13. [Trade-Offs & Rationale](#13-trade-offs--rationale)

---

## 1. Design Philosophy

### Principles

1. **Ordering is non-negotiable.** Every message must have a globally agreed position in the stream. Seq numbers are the source of truth — not timestamps, not client IDs.
2. **Single source of truth for messages.** DynamoDB is the authoritative message store. PostgreSQL holds metadata only.
3. **Reads are optimized over writes.** Chat is read-heavy (history browsing, search). Writes are append-only and must be cheap.
4. **Reconnection must be transparent.** The protocol must support catching up on missed messages without HTTP probing.
5. **Frontend state is derived, not cached.** The store holds an exact replica of server state. Optimistic updates are flagged and reconciled.

### Comparison to Other Platforms

| Aspect | Discord | Slack | Telegram | Kraivor Chat v2 |
|--------|---------|-------|----------|-----------------|
| Message ordering | Snowflake ID | Timestamp | pts (server int) | Per-room seq counter |
| Store | Cassandra/Scylla | Custom + Elasticsearch | PostgreSQL + custom | DynamoDB (single table) |
| Reconnection | Gateway resume | Full reload | pts sync | SYNC_ROOMS delta |
| Topology | Guild-centric | Workspace-centric | User-centric | User-centric |
| Thread model | Replies inline | Side panel | Inline | Side panel (Slack-like) |

---

## 2. Data Store Decision Matrix

### Why Not One Database?

| Requirement | PostgreSQL | DynamoDB | Redis | S3 |
|------------|-----------|----------|-------|-----|
| ACID transactions | ✅ Native | ❌ Limited | ❌ | ❌ |
| Relational joins (room→members→roles) | ✅ JOINs | ❌ Requires denormalization | ❌ | ❌ |
| Unlimited write scaling | ❌ Row count limits, vacuum | ✅ Partition-based scaling | ❌ Memory-bound | ❌ Not for structured data |
| Cursor pagination | ⚠️ Offset-based (slow) | ✅ Native ExclusiveStartKey | ❌ | ❌ |
| TTL-based expiry | ❌ No native TTL | ✅ TTL attribute | ✅ SETEX | ❌ Lifecycle policies |
| Binary blob storage | ❌ BLOBs bloat backups | ❌ 400KB item limit | ❌ | ✅ Designed for this |
| Sub-millisecond reads | ⚠️ Index + disk | ✅ Single-digit ms | ✅ < 1ms | ❌ Network latency |
| Full-text search | ✅ pg_trgm, tsvector | ⚠️ `contains` scan only | ❌ | ❌ |

### Decision: Multi-Store

| Store | Responsibilities | Access Pattern |
|-------|-----------------|----------------|
| **PostgreSQL** | Room metadata, membership, roles, pins, drafts, invites, unread counters, scheduled messages, notification preferences | Primary key lookups, filtered indexes |
| **DynamoDB** | Messages, thread replies, reactions, edits, read receipts, mentions, polls, voice notes, emoji reactions | Partition+sort key queries, type-discriminated |
| **Redis** | Presence, typing indicators, voice sessions, socket room membership, latest seq cache | TTL-based SET/GET, Pub/Sub broadcast |
| **S3** | Images, videos, PDFs, files, voice recordings, screen recordings | Pre-signed URL upload/download |

---

## 3. PostgreSQL Schema Design

### Entity-Relationship

```
┌─────────────┐       ┌──────────────────┐       ┌──────────────────┐
│   Room      │       │   RoomMember     │       │     Role         │
│─────────────│       │──────────────────│       │──────────────────│
│ id (PK)     │──1:N──│ room_id (FK)     │       │ id (PK)          │
│ room_type   │       │ user_id          │──1:N──│ room_id (FK)     │
│ name        │       │ last_read_seq    │       │ name             │
│ workspace   │       │ joined_at        │       │ color            │
│ (nullable)  │       └──────────────────┘       │ priority         │
│ is_public   │                                  │ can_* flags      │
│ message_c   │       ┌──────────────────┐       └────────┬─────────┘
│ member_c    │       │  RoomMemberRole  │                 │
│ last_msg_*  │       │──────────────────│                 │
└─────────────┘       │ member_id (FK)   │◄────────────────┘
                       │ role_id (FK)     │
                       └──────────────────┘

┌─────────────┐       ┌──────────────────┐
│ Draft       │       │  PinnedMessage   │
│─────────────│       │──────────────────│
│ room_id(FK) │       │ room_id (FK)     │
│ user_id     │       │ message_seq      │
│ content     │       │ pinned_by        │
│ reply_to    │       └──────────────────┘
│ attachments │
└─────────────┘
```

### Index Strategy

Every index is named explicitly for maintainability:

| Index Name | Table | Columns | Purpose |
|-----------|-------|---------|---------|
| `idx_room_type_recent` | rooms | `(room_type, -last_message_at)` | Sidebar listing: show recent rooms of each type |
| `idx_room_workspace` | rooms | `(workspace_id)` | Lookup team group by workspace |
| `idx_room_creator` | rooms | `(created_by)` | User's created rooms |
| `idx_member_user_room` | members | `(user_id, room)` | User's membership lookups |
| `idx_member_user_recent` | members | `(user_id, -joined_at)` | User's recently joined rooms |
| `idx_role_room_priority` | roles | `(room, priority)` | Role list sorted by rank |
| `idx_pinned_room_recent` | pins | `(room, -pinned_at)` | Pinned messages in a room |
| `idx_draft_room_user` | drafts | `(room, user_id)` | Unique per user per room |
| `idx_invite_user_status` | invites | `(target_user_id, status)` | Pending invites for a user |
| `idx_scheduled_pending` | scheduled | `(send_at, is_sent)` | Due scheduled messages |

### Soft Delete

All entities use soft delete (`deleted_at` timestamp, null when active). The `TimestampedModel` base class provides this automatically. Queries exclude soft-deleted rows by default.

---

## 4. DynamoDB Single-Table Design

### Table Configuration

| Property | Value |
|----------|-------|
| Table name | `kraivor-chat-v2` |
| Billing | On-demand (or Provisioned with auto-scaling) |
| Partition key | `room_id` (String) |
| Sort key | `sort_key` (String) |
| TTL attribute | `ttl` (optional, for ephemeral items) |

### Sort Key Format

```
{type}#{seq:020d}

type      = MSG | THREAD | REACT | EDIT | READ | DELETE
seq:020d  = zero-padded to 20 digits for lexicographic ordering
```

### Complete Sort Key Examples

| Entity | sort_key | Attributes |
|--------|----------|------------|
| Message | `MSG#00000000000000000001` | message_id, sender_id, sender_name, content, reply_to_seq, mention_user_ids, attachment_urls, is_edited, created_at |
| Thread reply | `THREAD#00000000000000000001#00000000000000000002` | message_id, parent_seq=1, seq=2, sender_id, content, created_at |
| Reaction | `REACT#00000000000000000001#user_uuid#👍` | target_seq=1, user_id, emoji, created_at |
| Edit record | `EDIT#00000000000000000001#00000000000000000005` | target_seq=1, seq=5, previous_content, new_content, edited_by, edited_at |
| Read receipt | `READ#user_uuid` | reader_id, read_up_to_seq, read_at |
| Deletion record | `DELETE#00000000000000000001#00000000000000000006` | target_seq=1, seq=6, deleted_by, deleted_at |
| Counter | `_counter` | next_seq (Atomic number) |

### Query Patterns

```
# 1. Get recent messages (infinite scroll)
QUERY: room_id = :rid AND begins_with(sort_key, "MSG#")
  → ScanIndexForward: false, Limit: 50
  → Paginate via ExclusiveStartKey using last sort_key

# 2. Get messages since seq N (reconnection sync)
QUERY: room_id = :rid AND sort_key > "MSG#00000000000000000042"
  → Limit: 200, ScanIndexForward: true

# 3. Get thread replies for a message
QUERY: room_id = :rid AND begins_with(sort_key, "THREAD#00000000000000000001#")
  → ScanIndexForward: true

# 4. Get reactions for a message
QUERY: room_id = :rid AND begins_with(sort_key, "REACT#00000000000000000001#")

# 5. Get a single message by seq
GET: room_id = :rid, sort_key = "MSG#00000000000000000042"

# 6. Get read receipt for a user
GET: room_id = :rid, sort_key = "READ#{user_id}"
```

### Item Size Considerations

- Each message item is approximately 200-500 bytes (excluding content)
- Content is stored as-is (text). Maximum DynamoDB item size is 400KB
- For messages approaching this limit, content should be stored in S3 with a reference URL
- The `seq:020d` sort key format adds 26 bytes per item — negligible

---

## 5. Atomic Seq Counter

### How It Works

Every room has exactly one counter item in DynamoDB:

```
room_id = "0194f8c2-..."
sort_key = "_counter"
next_seq = 42
```

**Allocation (pseudocode):**
```
response = UpdateItem(
  Key={room_id, sort_key="_counter"},
  UpdateExpression="ADD next_seq :inc",
  ExpressionAttributeValues={":inc": 1},
  ReturnValues="UPDATED_NEW"
)
seq = response["Attributes"]["next_seq"]  # returns new value
```

This is:
- **Atomic**: DynamoDB's `ADD` is a single ACID operation. Concurrent calls get different values.
- **Monotonic**: Seq numbers always increase. No gaps unless a write fails after counter increment (acceptable).
- **Fast**: Counter items are tiny (~20 bytes). DynamoDB Adaptive Capacity handles single-item hotspots.

### Initialization

When a room is created:
```
PutItem(
  Item={room_id, sort_key="_counter", next_seq=1},
  ConditionExpression="attribute_not_exists(sort_key)"
)
```

This is idempotent — if the counter already exists (e.g., race condition), the `ConditionExpression` fails silently.

### Why Not PostgreSQL for the Counter?

PostgreSQL sequences are simpler but would add a cross-store dependency. Keeping the counter in DynamoDB means:
- The entire message write path is within one store
- No two-phase commit between PostgreSQL and DynamoDB
- Counter latency is the same as message write latency

---

## 6. Redis Key Design

### Keyspace

| Key Pattern | Type | TTL | Purpose |
|------------|------|-----|---------|
| `presence:user:{user_id}` | String | 60s | Current presence status: `ONLINE`, `AWAY`, `DND` |
| `typing:room:{room_id}` | Set | 5s | Set of user IDs currently typing |
| `typing:room:{room_id}:last:{user_id}` | String | 5s | Last typing dispatch timestamp (for throttling) |
| `voice:room:{room_id}` | Set | — | Users in active voice session |
| `cache:room:{room_id}:latest_seq` | String | 30s | Cached latest seq to avoid DynamoDB query |

### Presence Lifecycle

```
1. WebSocket OPEN → SETEX presence:user:{id} 60 ONLINE
2. Heartbeat (every 30s) → EXPIRE presence:user:{id} 60
3. No heartbeat for 5min → Redis automatically expires key
4. WS CLOSE → PUBLISH presence:OFFLINE → DEL presence:user:{id}
5. Presence changes → PUBLISH to user's notification group
```

### Typing Throttle

```
User stops typing → emit { action: "TYPING", status: "STOP" }
User starts typing:
  1. GET typing:room:{room_id}:last:{user_id}
  2. If exists and < 2.5s old → skip (throttled)
  3. Else → SETEX 5s → emit { action: "TYPING", status: "START" }
  4. SADD typing:room:{room_id} {user_id}
  5. Auto-expire after 5s → removes from set
```

### Read Cache

To avoid a DynamoDB query for every `CONNECTED` event, the latest seq per room is cached:

```
On message send:
  SETEX cache:room:{room_id}:latest_seq 30d {seq}

On reconnect:
  latest_seq = GET cache:room:{room_id}:latest_seq
  if latest_seq: use for SYNC_ROOMS
  else: fallback to DynamoDB query
```

---

## 7. S3 Upload Flow

### Direct-to-S3 Upload

Files never pass through the Django server. The flow is:

```
Client                        Server                        S3
  │                             │                            │
  │  1. POST /api/chat/upload   │                            │
  │    { file_name, mime, size }│                            │
  │───────────────────────────►│                            │
  │                            │  2. Generate presigned PUT  │
  │                            │───────────────────────────►│
  │                            │◄───────────────────────────│
  │◄── { upload_url, file_id } │                            │
  │                            │                            │
  │  3. PUT file ────────────────────────────────────────►  │
  │◄────────────────────────────────────────────────────────│
  │                            │                            │
  │  4. POST /api/chat/confirm  │                            │
  │    { file_id }             │                            │
  │───────────────────────────►│                            │
  │                            │  5. Generate public URL    │
  │                            │───────────────────────────►│
  │                            │◄───────────────────────────│
  │◄── { public_url }         │                            │
```

### Benefits

- **No server-side file handling**: Zero memory/disk usage on Django for uploads
- **Parallel uploads**: Client uploads directly to S3 in parallel with message composition
- **Resumable**: Presigned URLs support multipart upload for large files
- **CDN-ready**: S3 + CloudFront for global low-latency asset delivery

### Bucket Structure

```
s3://kraivor-chat-assets/
├── chat/{room_id}/{file_id}.{ext}     # standard messages
├── threads/{room_id}/{file_id}.{ext}  # thread attachments
└── voice/{room_id}/{file_id}.ogg      # voice notes
```

---

## 8. Data Flow Diagrams

### 8.1 Send Message

```
User types → Enter

┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                      │
│                                                               │
│  ChatInput → ChatRoomPage.handleSend()                        │
│    → chatSocket.send({ action: "SEND", ... })                 │
│    → Optimistic: messageStore.addMessage(roomId, tempMsg)     │
│    → Virtualized list re-renders (O(1) Map insert)           │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ DJANGO (ChatConsumer._handle_send)                            │
│                                                               │
│  Step 1: Verify membership (RoomMember lookup)                │
│    → If not member: send ERROR → STOP                         │
│                                                               │
│  Step 2: Allocate seq                                         │
│    → DynamoDB UpdateItem ADD next_seq on _counter item        │
│    → Returns seq (e.g., 48)                                   │
│                                                               │
│  Step 3: Write message                                        │
│    → DynamoDB PutItem(room_id, "MSG#00000000000000000048",...)│
│                                                               │
│  Step 4: Update room metadata (async DB)                      │
│    → PostgreSQL: UPDATE rooms SET                             │
│        last_message_content, last_message_at,                 │
│        message_count += 1                                     │
│                                                               │
│  Step 5: Broadcast to room group (channel layer)              │
│    → group_send("room_{id}", { type: "chat.message", ... })   │
│    → All OTHER clients in room receive MESSAGE event          │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Receive Message (Other Clients)

```
┌─────────────────────────────────────────────────────────────┐
│ DJANGO (Channel Layer)                                        │
│                                                               │
│  ChatConsumer.chat_message(event)                              │
│    → Checks _exclude_user_id (skip sender)                    │
│    → Sends JSON via WebSocket: { type: "MESSAGE", ... }      │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                      │
│                                                               │
│  ChatSocket.onEvent → messageStore.addMessage(roomId, msg)   │
│    → Map.set(seq, msg) — O(1)                                │
│    → If room not active: chatStore.incrementUnread(roomId)   │
│    → Virtualized list measures + re-renders affected item    │
│                                                               │
│  If message contains @mention:                                │
│    → Play notification sound                                  │
│    → Show toast notification (sonner)                         │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 Reconnection Sync

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                      │
│                                                               │
│  WebSocket drops → ChatSocket detects onclose                │
│    → Exponential backoff reconnect (1s–30s, jitter)          │
│    → On CONNECTED:                                           │
│        → Emit SYNC_ROOMS with { room_id, last_seen_seq }     │
│          for all subscribed rooms                             │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ DJANGO (ChatConsumer._handle_sync_rooms)                      │
│                                                               │
│  For each room in request:                                    │
│    1. DynamoDB Query: room_id + sort_key > "MSG#{seq:020d}"  │
│       → Returns messages with seq > last_seen_seq             │
│       → Limit: 200 per room                                  │
│    2. Send SYNC event: { room_id, messages[], upto_seq }     │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                      │
│                                                               │
│  messageStore.addMessages(roomId, msgs) — O(n) bulk insert   │
│  Virtualized list scrolls if needed                           │
│  Updates last_seen_seq in local state                         │
└─────────────────────────────────────────────────────────────┘
```

### 8.4 Thread Reply

```
User clicks reply on message → thread panel opens
  → chatStore.openThread(parentSeq)

User types in thread input → emits { action: "THREAD_REPLY", ... }
  → Server allocates seq → stores with sort_key "THREAD#{parentSeq}#{seq}"
  → Broadcasts THREAD_REPLY event to room group

Thread panel sees new reply → messageStore.addMessage(roomId, reply)
  → But also stored in separate thread view state
```

### 8.5 Workspace → Team Group Sync

```
┌──────────────┐         ┌──────────────────┐
│  Workspace   │         │  Team Group Room │
│  Created     │──signal─►  Auto-created    │
│              │         │  Owner added as  │
│              │         │  first member    │
└──────────────┘         └──────────────────┘

┌──────────────┐         ┌──────────────────┐
│  Workspace   │         │  Team Group      │
│  Member      │──signal─►  RoomMember      │
│  Created     │         │  Created         │
└──────────────┘         └──────────────────┘

┌──────────────┐         ┌──────────────────┐
│  Workspace   │         │  Team Group      │
│  Member      │──signal─►  RoomMember      │
│  Deleted     │         │  Deleted         │
└──────────────┘         └──────────────────┘
```

---

## 9. Consistency Model

### Write Path

| Operation | Consistency | Rationale |
|-----------|-------------|-----------|
| Send message (counter + put) | Strong (DynamoDB atomic counter) | Seq number must be unique and monotonic |
| Room metadata update | Strong (PostgreSQL row lock) | `message_count += 1` must be accurate |
| Membership sync (signal) | Strong (Django transaction.atomic) | Workspace member ↔ room member must be atomic |
| Typing indicator | Eventual (Redis TTL) | Lost typing events are harmless |
| Presence | Eventual (Redis TTL expiry) | 60s stale presence is acceptable |

### Read Path

| Operation | Consistency | Rationale |
|-----------|-------------|-----------|
| Message history | Eventually consistent (DynamoDB) | New writes visible within milliseconds |
| Room list | Strong (PostgreSQL) | Membership must be current |
| Unread count | Read from PostgreSQL | `last_read_seq` on RoomMember is source of truth |
| Latest seq cache | Eventually consistent (Redis 30s TTL) | Stale seq means extra sync on reconnect (harmless) |

### Conflict Resolution

| Conflict | Resolution |
|----------|-----------|
| Concurrent sends in same room | Atomic counter guarantees different seq numbers. Order is seq-based. |
| Concurrent edits to same message | Last write wins. Seq counter ensures determinism. |
| Concurrent member add/remove | Handled by Django's `select_for_update` row lock. |
| Reconnect before DynamoDB write completes | Message is in DynamoDB before `chat_message` broadcast. Broadcast already has the data. |

---

## 10. Scalability Design

### PostgreSQL

| Concern | Mitigation |
|---------|------------|
| `messages_count` updates | Denormalized counter; no COUNT(*) queries |
| Room listing for 10k users per workspace | Indexed by `(user_id, room)` — covers all queries |
| Drafts for millions of users | Indexed by `(room, user_id)` — unique constraint prevents duplicates |
| Scheduled messages at scale | Indexed by `(send_at, is_sent)` — pulls only pending messages |

### DynamoDB

| Concern | Mitigation |
|---------|------------|
| Hot partition (busy room) | DynamoDB Adaptive Capacity handles single-PK hotspots. Counter item is tiny. |
| Large message content | Store content in S3 for messages > 32KB; store URL in DynamoDB |
| Pagination depth | Cursor-based via `ExclusiveStartKey`. No offset limits. |
| Item size (400KB cap) | Thread replies, reactions, edits each have their own items. Single message rarely exceeds 400KB. |

### Redis

| Concern | Mitigation |
|---------|------------|
| Memory usage | Presence keys: ~100 bytes per online user. Typing: ~50 bytes per typing user. Total for 100k online users ~ 15MB. |
| Pub/sub scaling | Redis Cluster for multi-node deployments. Channel layer shards by room. |

### Frontend

| Concern | Mitigation |
|---------|------------|
| 10k rooms in sidebar | Virtualized via `@tanstack/react-virtual`. Only ~20 DOM nodes rendered. |
| 100k messages in a room | Virtualized message list. Only visible items (plus overscan) in DOM. |
| State update storms | Map-based O(1) inserts. Batch DOM layout pass. Shallow Zustand selectors. |

---

## 11. Security Design

### Authentication

- WebSocket authenticated via JWT in query string: `ws://host/ws/chat/?token={jwt}`
- JWT verified via `JWTAuthMiddleware` against Identity Service's JWKS endpoint (RS256)
- Invalid/expired tokens → WebSocket closed with code 4001

### Authorization

| Operation | Check | Enforcement |
|-----------|-------|-------------|
| Send message | Must be `RoomMember` | `_is_member()` before every handler |
| Edit message | Must be sender | N/A (only sender has permission to edit their own) |
| Delete message | Must have `can_delete_messages` permission OR be sender | Check via `Role` → `RoomMemberRole` |
| Manage members | Must have `can_manage_members` permission | Role check |
| View room | Must be `RoomMember` | `_is_member()` on SUBSCRIBE |
| View public group | Anyone can subscribe (no membership check) | `Room.is_public = True` |

### XSS Prevention

- Message content is **not HTML-escaped on the server** — it is stored as Markdown text
- The frontend renders content via `react-markdown` which sanitizes output
- Attachment URLs are validated S3 presigned URLs — no arbitrary URLs
- Mention user IDs are UUIDs, not user-controlled strings

### Rate Limiting

| Action | Limit | Implementation |
|--------|-------|----------------|
| Message send | 30 per minute per user | Django middleware or DRF throttling |
| Typing START | 1 per 2.5s per user per room | Server-side throttle in consumer |
| WebSocket connect | 10 per minute per IP | Custom middleware |
| DynamoDB write | Pay-per-use | On-demand capacity |

---

## 12. Failure Modes

### 12.1 DynamoDB Write Failure After Counter Increment

**Scenario:** Counter is incremented but `PutItem` for the message fails.

**Impact:** A seq number is skipped (gap in sequence). The sender sees an error.

**Mitigation:** Seq gaps are harmless — they do not affect ordering. The sender retries and gets a new seq.

### 12.2 WebSocket Disconnect Before Client Receives Broadcast

**Scenario:** Server broadcasts a message, but the recipient's WebSocket disconnects before receiving it.

**Impact:** The recipient misses the real-time event.

**Mitigation:**
1. The message is safely stored in DynamoDB
2. On reconnect, `SYNC_ROOMS` catches the missed message via seq delta
3. No data loss — only a brief delay in visibility

### 12.3 PostgreSQL Unavailable During Send

**Scenario:** DynamoDB write succeeds but PostgreSQL update of room metadata fails.

**Impact:** Room's `last_message_*` and `message_count` are stale.

**Mitigation:** The metadata update is best-effort (wrapped in try/except with warning log). Stale metadata is cosmetic — it only affects sidebar preview. The message itself is safely stored in DynamoDB.

### 12.4 Race: Two Concurrent Edits to Same Message

**Scenario:** User A and User B both edit the same message simultaneously.

**Impact:** Last write wins. One edit overwrites the other.

**Mitigation:** Edit history is stored in DynamoDB (`EDIT#{seq}`). The previous content is preserved in the edit record. An "undo" feature could restore from edit history.

### 12.5 Redis Outage

**Scenario:** Redis is unavailable.

**Impact:**
- Presence shows all users as offline (stale)
- Typing indicators stop working
- Channel layer falls back (if configured with fallback)
- Message delivery is unaffected (uses PostgreSQL + DynamoDB only)

**Mitigation:** Presence and typing are cosmetic features. Core messaging continues without Redis.

---

## 13. Trade-Offs & Rationale

### 13.1 DynamoDB Single Table vs. Multiple Tables

**Chosen:** Single table with type discriminator.

| Pro | Con |
|-----|-----|
| Fewer connections, simpler IAM | Type-prefixed queries require `begins_with` |
| Cross-entity queries possible (reactions + edits in one request) | Harder to reason about RCU/WCU per entity type |
| One table to monitor, backup, scale | Sort key design must be planned upfront |

**Why this wins:** Chat query patterns are always scoped to a single room. Within a room, asking for "messages + reactions" is common. A single table allows a single query with `sort_key BETWEEN` to fetch multiple types.

### 13.2 Atomic Counter in DynamoDB vs. PostgreSQL

**Chosen:** DynamoDB atomic counter.

| Pro | Con |
|-----|-----|
| Single-store write path | Additional WCU on counter item |
| No cross-store two-phase commit | Counter item is a hot key on busy rooms |
| Same latency as message write | DynamoDB has no `SELECT FOR UPDATE` — relies on `ADD` atomicity |

**Why this wins:** Two-phase commit between PostgreSQL and DynamoDB adds complexity with zero benefit. The counter is tiny (~20 bytes) and Adaptive Capacity handles hotspots.

### 13.3 Global WebSocket vs. Per-Room WebSocket

**Chosen:** Single global WebSocket.

| Pro | Con |
|-----|-----|
| One connection per user (resource efficiency) | Client-side subscription routing required |
| SYNC_ROOMS can catch up all rooms in one batch | Server must manage subscription state per connection |
| Simpler reconnection logic | Larger message router in consumer |

**Why this wins:** Per-room sockets required N connections per user (one per active room). At 10 rooms per user, that's 10x the connection overhead on both client and server.

### 13.4 Soft Delete vs. Hard Delete

**Chosen:** Soft delete (DynamoDB `is_deleted` flag + audit record).

| Pro | Con |
|-----|-----|
| Audit trail preserved | Storage for deleted data |
| Undo possible (within time window) | Queries must filter `is_deleted = false` |
| Compliance (regulatory requirement for message retention) | — |

**Why this wins:** Many jurisdictions require message retention for compliance. Soft delete satisfies this while still removing content from the user-facing view.

### 13.5 Virtualized List vs. Paginated List

**Chosen:** Virtualized list (`@tanstack/react-virtual`).

| Pro | Con |
|-----|-----|
| Constant DOM size (regardless of message count) | Must measure item heights or use fixed estimates |
| 60fps scrolling at any scale | Infinite scroll upward adds complexity |
| O(1) memory per visible item | Scroll position must be maintained on re-render |

**Why this wins:** A flat DOM with 10,000+ message nodes causes layout thrashing, memory pressure, and janky scrolling. Virtualization keeps DOM nodes at ~30-50 regardless of total message count.
