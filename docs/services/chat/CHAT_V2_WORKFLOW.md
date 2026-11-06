# Kraivor Chat v2 — Workflows

> **Document Version:** 1.0  
> **Last Updated:** 2026-07-09  
> **Service:** Core Service — Chat Rebuild  
> **Status:** Approved — In Development  
> **Classification:** Internal — Workflow Reference

**Related Documents:**
- [`CHAT_V2_OVERVIEW.md`](./CHAT_V2_OVERVIEW.md) — Executive summary, topology, goals
- [`CHAT_V2_SYSTEM_DESIGN.md`](./CHAT_V2_SYSTEM_DESIGN.md) — Design rationale, decision matrix, data flow diagrams, trade-offs
- [`CHAT_V2_ARCHITECTURE.md`](./CHAT_V2_ARCHITECTURE.md) — Implementation blueprint, models, protocol, stores, file map, phases

---

## Table of Contents

1. [Connection Lifecycle](#1-connection-lifecycle)
2. [Message Send Flow](#2-message-send-flow)
3. [Message Receive Flow](#3-message-receive-flow)
4. [Reconnection & Sync](#4-reconnection--sync)
5. [Room Lifecycle](#5-room-lifecycle)
6. [Workspace Team Group Auto-Provisioning](#6-workspace-team-group-auto-provisioning)
7. [File Upload Flow](#7-file-upload-flow)
8. [Thread Reply Flow](#8-thread-reply-flow)
9. [Reaction Flow](#9-reaction-flow)
10. [Edit & Delete Flow](#10-edit--delete-flow)
11. [Migration Flow](#11-migration-flow)
12. [Error Recovery](#12-error-recovery)

---

## 1. Connection Lifecycle

### 1.1 Initial Connection

```
User opens app / navigates to chat
         │
         ▼
  Frontend: ChatSocket.connect()
    → ws://host/ws/chat/?token={jwt}
         │
         ▼
  Django: ChatConsumer.connect()
    → Verify JWT, extract user_id
    → Initialize: user_group = "user_{id}"
    → Send CONNECTED event:
         {
           type: "CONNECTED",
           user_id,
           rooms: [{ room_id, last_seq }, ...],
           server_time
         }
    → Start heartbeat monitor
         │
         ▼
  Frontend: chatSocket.onConnected()
    → Update connectionStore: status = "connected"
    → For each room in user's membership list:
        → SUBSCRIBE with last_seen_seq (from local store or server-provided last_seq)
    → If rooms with pending unreads → trigger sync
```

### 1.2 Heartbeat

```
Every 30 seconds:
  Client → Server: { action: "HEARTBEAT" }
  Server: EXPIRE presence:user:{id} 60 (refresh presence TTL)
```

### 1.3 Graceful Disconnect

```
User closes tab / navigates away
         │
         ▼
  Frontend: ChatSocket.disconnect()
    → Send { action: "PRESENCE", status: "OFFLINE" }
    → Close WebSocket
         │
         ▼
  Django: ChatConsumer.disconnect()
    → DEL presence:user:{id}
    → For each subscribed room: group_discard("room_{id}")
    → Broadcast PRESENCE:OFFLINE to user's channel group
    → Remove from any voice sessions
```

---

## 2. Message Send Flow

### Step-by-Step

```
User types in ChatInput → presses Enter
         │
         ▼
  FRONTEND (chat-input.tsx)
    ├── Validate: non-empty content or attachments
    ├── Generate temp_id (client-side UUID)
    ├── Optimistic insert:
    │     messageStore.addMessage(roomId, {
    │       seq: -1 (placeholder),
    │       message_id: temp_id,
    │       sender_id: currentUser.id,
    │       content,
    │       status: "sending"
    │     })
    └── Emit WebSocket: { action: "SEND", room_id, content, ... }
         │
         ▼
  DJANGO (ChatConsumer._handle_send)
    ├── Step 1: Verify membership
    │     └── RoomMember.objects.get(room_id=rid, user_id=uid)
    │           └── FAIL → send ERROR("PERMISSION_DENIED") → STOP
    │
    ├── Step 2: Allocate seq number
    │     └── DynamoDB: UpdateItem ADD next_seq :1 on _counter
    │           └── Returns seq (e.g., 48)
    │
    ├── Step 3: Write message to DynamoDB
    │     └── PutItem(room_id, sort_key="MSG#{seq:020d}", {
    │           message_id, sender_id, sender_name,
    │           content, reply_to_seq, mention_user_ids,
    │           attachment_urls, is_edited=false, created_at
    │         })
    │
    ├── Step 4: Update room metadata (async, non-blocking)
    │     └── database_sync_to_async:
    │           Room.objects.filter(id=rid).update(
    │             last_message_content=content,
    │             last_message_at=now,
    │             last_message_sender_name=sender_name,
    │           )
    │           RoomMember.objects.filter(room_id=rid).exclude(user_id=uid)
    │             .update(last_read_seq=seq)
    │
    ├── Step 5: Update Redis cache
    │     └── SETEX cache:room:{rid}:latest_seq 30d {seq}
    │
    └── Step 6: Broadcast to room group
          └── group_send("room_{rid}", {
                type: "chat.message",
                seq, message_id, sender_id, sender_name,
                content, reply_to_seq, mention_user_ids,
                attachment_urls
              })
                └── Other clients receive MESSAGE event (see §3)
                └── Sender excluded via _exclude_user_id
         │
         ▼
  FRONTEND (sender)
    ├── Receive broadcast NOT for sender (excluded)
    └── But: our optimistic insert already rendered it
         └── On ACK (implicit via local state):
               messageStore.updateMessageStatus(roomId, temp_id, "sent")
               └── Replace seq:-1 with actual seq from local tracking
```

### Seq Allocation Detail

See `CHAT_V2_ARCHITECTURE.md §8` for the DynamoDB `UpdateItem ADD` implementation. The key invariant: **seq is allocated before the message write**, so concurrent senders never collide.

---

## 3. Message Receive Flow

### 3.1 Other Clients (Broadcast Recipients)

```
  Channel Layer → group_send("room_{rid}", { type: "chat.message", ... })
         │
         ▼
  ChatConsumer.chat_message(event)
    ├── Skip if event.user_id == self.user_id (exclude sender)
    └── Send via WebSocket: { type: "MESSAGE", room_id, seq, ... }
         │
         ▼
  FRONTEND (chatSocket.onEvent)
    ├── Route by event type → "MESSAGE"
    │
    ├── If room is NOT currently subscribed:
    │     └── chatStore.incrementUnread(roomId)
    │         └── Sidebar shows unread badge
    │
    ├── If room IS currently subscribed:
    │     └── messageStore.addMessage(roomId, msg)
    │           ├── Map.set(seq, msg) — O(1)
    │           └── If room is active tab:
    │                 ├── Virtualized list re-renders affected item
    │                 └── Auto-scroll to bottom if already near bottom
    │
    ├── If @mention detected (mention_user_ids includes currentUser):
    │     ├── Play notification sound
    │     ├── Show toast (sonner)
    │     └── Windows flash / tab title badge
    │
    └── Update last_seen_seq in local state
```

### 3.2 Reconnect Catch-Up

When a client reconnects after being offline, the `SYNC_ROOMS` flow (§4) delivers missed messages as a `SYNC` event batch rather than individual `MESSAGE` events.

---

## 4. Reconnection & Sync

### 4.1 Detection & Backoff

```
  WebSocket drops (onclose)
         │
         ▼
  FRONTEND (chatSocket)
    ├── connectionStore.setStatus("disconnected")
    ├── Start exponential backoff:
    │     delay = min(1000 * 2^attempt + jitter, 30000)
    │     attempt++
    │     setTimeout(connect, delay)
    └── On reconnect attempt:
          ├── If success → reset attempt = 0
          └── If fail → next backoff cycle
```

### 4.2 Reconnect & Sync

```
  WebSocket successfully reconnected
         │
         ▼
  Django: ChatConsumer.connect()
    └── Send CONNECTED event (as in §1.1)
         │
         ▼
  FRONTEND: onConnected()
    ├── connectionStore.setStatus("connected")
    ├── Collect all subscribed rooms + their last_seen_seq
    │     (from messageStore.getHighestSeq(roomId) per room)
    └── Emit: { action: "SYNC_ROOMS", rooms: [...] }
         │
         ▼
  Django: ChatConsumer._handle_sync_rooms()
    ├── For each room in request:
    │     ├── DynamoDB Query:
    │     │     room_id = :rid
    │     │     AND sort_key BEGINS_WITH "MSG#"
    │     │     AND sort_key > "MSG#{last_seen_seq:020d}"
    │     │     Limit: 200
    │     │     ScanIndexForward: true
    │     │
    │     └── Send SYNC event:
    │           { type: "SYNC", room_id, messages: [...], upto_seq }
    │
    └── For each room NOT in request but user is member:
          └── Send SYNC with empty messages[] + cur_seq
               (so frontend knows last_seq without querying)
         │
         ▼
  FRONTEND: onSync()
    ├── messageStore.addMessages(roomId, msgs) — O(n) bulk
    ├── Update local last_seen_seq for room
    ├── If room is active tab:
    │     └── Scroll to last message (or show "N new messages" bar)
    └── Re-subscribe to all rooms (SUBSCRIBE with updated seq)
```

### 4.3 Optimistic Path (Redis Cache)

On reconnect, the server can optionally use Redis `GET cache:room:{rid}:latest_seq` to provide the latest seq in the `CONNECTED` event, avoiding a DynamoDB query per room. If the cache is cold (key expired), fallback to DynamoDB.

---

## 5. Room Lifecycle

### 5.1 Create Room

```
  User: "New Direct Message" or "New Group"
         │
         ▼
  FRONTEND → POST /api/chat/rooms
    { room_type: "DM" | "GROUP", name?, member_ids: [...] }
         │
         ▼
  DJANGO (create_room view/service)
    ├── Validate: non-empty member_ids
    ├── If DM:
    │     ├── Check existing DM: Room.objects.filter(
    │     │     room_type="DM", members__user_id__in=[uid1, uid2]
    │     │   ).annotate(member_count=Count("members"))
    │     │   .filter(member_count=2).exists()
    │     │   → If exists: return existing room (no duplicate)
    │     └── Create new DM room
    │
    ├── If GROUP:
    │     └── Create with creator as admin
    │
    ├── Create Room in PostgreSQL
    ├── Create RoomMember entries for all initial members
    ├── Initialize DynamoDB counter:
    │     PutItem(room_id, sort_key="_counter", next_seq=1)
    │     Condition: attribute_not_exists(sort_key)
    │
    └── Return room metadata + membership info
         │
         ▼
  FRONTEND
    ├── chatStore.addRoom(room)  → sidebar re-renders
    ├── Open room tab if user navigates there
    └── SUBSCRIBE to new room via WebSocket
```

### 5.2 Invite Members

```
  User: Right panel → Members → Invite
    → POST /api/chat/rooms/{id}/invite { user_ids: [...] }
         │
         ▼
  DJANGO
    ├── Verify inviter has can_manage_members permission
    ├── Create RoomInvite entries per user
    └── Send notification to target users
         │
         ▼
  Target user receives notification
    → GET /api/chat/invites → see pending invites
    → POST /api/chat/invites/{id}/accept
    → POST /api/chat/invites/{id}/decline
```

### 5.3 Join (Public Groups)

```
  User: Discover → Public group listing
    → POST /api/chat/rooms/{id}/join
         │
         ▼
  DJANGO
    ├── Verify room.is_public and room_type="GROUP"
    ├── Create RoomMember entry
    ├── Optionally: trigger DynamoDB read receipt init
    └── Broadcast presence change to room members
```

### 5.4 Leave Room

```
  User: Right panel → Leave Room
    → DELETE /api/chat/rooms/{id}/members/me
         │
         ▼
  DJANGO
    ├── Soft-delete RoomMember (deleted_at = now)
    ├── If last member: mark room as archived
    └── Server-side: remove from WebSocket room group
         │
         ▼
    WebSocket: group_send("room_{id}", {
      type: "chat.member_left", user_id
    })
         │
         ▼
  FRONTEND
    ├── Remove room from chatStore
    ├── Close tab if active
    └── messageStore.clearRoom(roomId)
```

### 5.5 Archive / Delete Room

- **Archive**: Soft-delete Room (`deleted_at`), hide from sidebar, retain messages in DynamoDB.
- **Delete**: Set `deleted_at` on Room + cascade soft-delete to RoomMember, Draft, PinnedMessage. DynamoDB items remain (no cascade delete from PostgreSQL to DynamoDB). TTL-based cleanup optional.

---

## 6. Workspace Team Group Auto-Provisioning

This workflow is driven by Django signals — no manual room creation needed for workspace communication.

### 6.1 Workspace Created → Team Group Provisioned

```
  post_save(Workspace, created=True)
         │
         ▼
  signals.py: provision_team_group(sender, instance, created)
    ├── Check: Room.objects.filter(workspace_id=ws.id).exists()
    │     └── If exists → return (idempotent)
    │
    ├── Create Room:
    │     room_type = "WORKSPACE_TEAM"
    │     name = f"{ws.name} Team"
    │     workspace_id = ws.id
    │     is_public = False (implicitly private to workspace members)
    │     created_by = ws.owner_id
    │
    ├── Create RoomMember for workspace owner
    ├── Initialize DynamoDB counter (_counter, next_seq=1)
    │
    └── Optionally broadcast to real-time group:
          { type: "ROOM_CREATED", room }
```

### 6.2 User Joins Workspace → Added to Team Group

```
  post_save(WorkspaceMember, created=True)
         │
         ▼
  signals.py: add_to_team_group(sender, instance, created)
    ├── Find Room: workspace_id = member.workspace_id, room_type="WORKSPACE_TEAM"
    ├── Create RoomMember entry (if not exists)
    └── If user connected via WebSocket:
          → group_add("room_{team_group_id}")
          → Send { type: "ROOM_ADDED", room_id, room_name }
```

### 6.3 User Leaves Workspace → Removed from Team Group

```
  post_delete(WorkspaceMember)
         │
         ▼
  signals.py: remove_from_team_group(sender, instance)
    ├── Find Room: workspace_id = member.workspace_id, room_type="WORKSPACE_TEAM"
    ├── Soft-delete RoomMember entry
    └── If user connected via WebSocket:
          → group_discard("room_{team_group_id}")
          → Send { type: "ROOM_REMOVED", room_id }
```

### 6.4 Workspace Deleted → Team Group Archived

```
  post_save(Workspace, is_deleted=True)  or  post_delete(Workspace)
         │
         ▼
  signals.py: archive_team_group(sender, instance)
    ├── Find Room: workspace_id = ws.id, room_type="WORKSPACE_TEAM"
    ├── Soft-delete Room (deleted_at = now)
    ├── Soft-delete all RoomMember entries
    └── Broadcast to all members: { type: "ROOM_ARCHIVED", room_id }
```

---

## 7. File Upload Flow

Files never pass through the Django server. Direct-to-S3 upload via presigned URLs.

### Step-by-Step

```
  User: Drag file into ChatInput / paste image
         │
         ▼
  FRONTEND (uploadStore)
    ├── Step 1: Request presigned URL
    │     POST /api/chat/upload { file_name, mime, size }
    │         │
    │         ▼
    │     Django (PresignedUploadView)
    │       ├── Generate file_id (UUID)
    │       ├── Construct S3 key: chat/{room_id}/{file_id}.{ext}
    │       ├── Generate presigned PUT URL (expires 1h)
    │       └── Return { upload_url, file_id, key }
    │
    ├── Step 2: Upload directly to S3
    │     PUT {upload_url} (presigned)
    │     Body: raw file bytes
    │     Content-Type: {mime}
    │         │
    │         ▼
    │     S3 returns 200 OK
    │
    ├── Step 3: Confirm upload
    │     POST /api/chat/confirm { file_id }
    │         │
    │         ▼
    │     Django
    │       ├── Verify file exists in S3 (HeadObject)
    │       ├── Generate public URL (or CloudFront CDN URL)
    │       └── Return { public_url, file_id, key }
    │
    ├── Step 4: Update uploadStore
    │     ├── Mark file as uploaded
    │     ├── Show thumbnail/preview in ChatInput
    │     └── Append URL to message attachment list
    │
    └── Step 5: Send message with attachments
          └── Same as §2, with attachment_urls populated
```

### Error Handling

| Failure | UX |
|---------|-----|
| Presign request fails (network/401) | Show error toast, retry button |
| S3 upload fails | uploadStore marks file as error, retry option |
| Confirm fails | File in S3 but orphaned — periodic S3 lifecycle policy cleans orphaned uploads |
| File exceeds limit | Validate client-side before presign request (max 100MB) |

---

## 8. Thread Reply Flow

### 8.1 Opening a Thread

```
  User clicks reply icon on message (seq=1)
         │
         ▼
  FRONTEND: chatStore.openThread(parentSeq=1)
    ├── Thread side panel opens (right side, slide-over on mobile)
    ├── If thread replies not yet loaded:
    │     └── DynamoDB: Query room_id + begins_with(sort_key, "THREAD#00000000000000000001#")
    │           → ScanIndexForward: true (oldest first)
    │           → Load into threadStore
    └── Scroll to bottom of thread replies
```

### 8.2 Sending a Thread Reply

Identical to message send (§2) but with action `THREAD_REPLY` and parent_seq.

```
  User types in thread input → Enter
    → Emit: { action: "THREAD_REPLY", room_id, parent_seq, content, ... }
    → Server allocates seq for the reply (room-level seq, not thread-local)
    → Writes DynamoDB: sort_key = "THREAD#{parent_seq:020d}#{seq:020d}"
    → Broadcasts THREAD_REPLY event to room group
    → Frontend thread panel receives reply → adds to threadStore
      → Auto-scrolls to bottom
```

### 8.3 Thread Layout

- Thread replies render in a vertical timeline below the parent message.
- Each reply shows sender avatar, name, timestamp, content, and can itself receive reactions.
- Threads do not nest further (no thread-of-thread).

---

## 9. Reaction Flow

```
  User clicks emoji picker on message (seq=1)
    → Emit: { action: "REACT", room_id, target_seq: 1, emoji: "👍" }
         │
         ▼
  Django: ChatConsumer._handle_reaction()
    ├── Verify message exists (DynamoDB GetItem for MSG#{seq})
    ├── DynamoDB PutItem:
    │     sort_key = "REACT#{target_seq:020d}#{user_id}#👍"
    │     ttl = optional (reactions can auto-expire)
    │
    └── Broadcast: { type: "REACTION", target_seq, user_id, user_name, emoji }
         │
         ▼
  FRONTEND: onReaction()
    ├── messageStore.addReaction(roomId, targetSeq, { user_id, emoji })
    └── Re-render affected message item — emoji count + who reacted

  Toggle off (same user + same emoji again):
    → DynamoDB DeleteItem(sort_key = "REACT#{seq}#{user_id}#👍")
    → Broadcast: { type: "REACTION_REMOVED", ... }
```

---

## 10. Edit & Delete Flow

### 10.1 Edit Message

```
  User: Right-click message → Edit → modify content → Save
    → Emit: { action: "EDIT", room_id, seq, content }
         │
         ▼
  Django: ChatConsumer._handle_edit()
    ├── Verify sender owns message (or has can_delete_messages permission)
    ├── DynamoDB PutItem: EDIT record (sort_key = "EDIT#{seq:020d}#{edit_seq}")
    ├── Update message: MSG#{seq} item → is_edited=true (if first edit)
    └── Broadcast: { type: "MESSAGE_EDITED", room_id, seq, content, edited_at }
         │
         ▼
  FRONTEND: onMessageEdited()
    ├── messageStore.updateMessageContent(roomId, seq, content)
    ├── Mark message as edited (show "(edited)" badge)
    └── If message is virtualized and visible → re-render
```

### 10.2 Delete Message

```
  User: Right-click message → Delete
    → Emit: { action: "DELETE", room_id, seq }
         │
         ▼
  Django: ChatConsumer._handle_delete()
    ├── Verify sender owns message OR has can_delete_messages permission
    ├── DynamoDB PutItem: DELETE record (sort_key = "DELETE#{seq}#{delete_seq}")
    ├── Set MSG#{seq} item's is_deleted=true (or overwrite content with "[deleted]")
    └── Broadcast: { type: "MESSAGE_DELETED", room_id, seq }
         │
         ▼
  FRONTEND: onMessageDeleted()
    ├── messageStore.deleteMessage(roomId, seq)
    │     └── Either: remove from Map entirely
    │         Or: replace content with "[deleted]" + dimmed style
    └── Re-render affected message item
```

---

## 11. Migration Flow

### Phase Timeline

| Phase | Frontend | Backend | State |
|-------|----------|---------|-------|
| **Phase 1-2** | New UI behind `?chat=v2` | New models, DynamoDB table, consumer deployed alongside old | Old chat = default |
| **Phase 3** | New UI = default, `?chat=v1` for old | Both stacks running | Dual-write if needed, otherwise read-only old |
| **Phase 4** | Old components removed | Old models, consumers, DynamoDB table dropped | Only v2 exists |

### Data Migration Notes

- **No message migration**. Legacy DynamoDB table `kraivor-chat-messages` remains untouched. Users start fresh in v2 rooms.
- Room metadata (PostgreSQL) is new schema — legacy models keep existing data until Phase 4 drop.
- Feature flag: `CHAT_V2_ENABLED` setting in Django + `?chat=v2` URL param for opt-in.

---

## 12. Error Recovery

### 12.1 Connection Drop

| Phase | Action |
|-------|--------|
| 0–1s drop | Immediate reconnect (no backoff yet) |
| 1–30s repeated drops | Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s |
| >30s offline | On reconnect: `SYNC_ROOMS` with all subscribed rooms |

### 12.2 Seq Gaps

If `SYNC_ROOMS` reveals a gap (e.g., frontend expected seq 1–50 but only gets 43–50):
- Frontend inserts a placeholder "N messages unavailable" at the gap point
- User can scroll up to trigger a backward pagination query
- Gaps should be rare — they only occur if a DynamoDB write succeeds but the counter increment failed, which would be an exceptional DynamoDB error

### 12.3 Permission Errors

| Error Code | Cause | Frontend Handling |
|-----------|-------|-------------------|
| `ROOM_NOT_FOUND` | Room deleted or never existed | Close tab, redirect to chat home |
| `PERMISSION_DENIED` | Not a member, no write permission | Show toast, disable input |
| `RATE_LIMITED` | Too many messages too fast | Show toast with cooldown timer, re-enable after delay |

### 12.4 DynamoDB Throttling

DynamoDB on-demand has adaptive capacity. If a hot partition (e.g., busy room) gets throttled:
- **Counter item**: Very unlikely (< 20 bytes, easily within a WCU)
- **Message writes**: Retry with exponential backoff (Django consumer catches `ProvisionedThroughputExceededException`)
- **Frontend**: Optimistic insert is already in the store. If server returns error, mark message as `failed` with retry button.

### 12.5 Optimistic Update Conflict

When frontend inserts an optimistic message (seq = -1 placeholder) and the server returns a conflicting seq:
- On receiving the `MESSAGE` broadcast (excluded for sender — but we track locally), the frontend replaces the placeholder seq with the real seq.
- If the real seq arrives and the placeholder had a different order (extremely rare — frontend inserts at end of list, seq preserves order), the list re-sorts by seq.

### 12.6 Signal Failure (Workspace Provisioning)

If the `post_save` signal handler for workspace creation fails:
- **Missing team group**: Next user entering workspace triggers the handler again (idempotent check on `Room.objects.filter(workspace_id=...)`)
- **If Django signal infrastructure is down**: Manual admin command `provision_missing_team_groups` scans workspaces without team groups and creates them
