# Kraivor Chat v2 — Overview

> **Document Version:** 1.0  
> **Last Updated:** 2026-07-09  
> **Service:** Core Service — Chat Rebuild  
> **Status:** Approved — In Development  
> **Classification:** Internal — Overview

---

## What Is Chat v2?

Chat v2 is a complete rebuild of Kraivor's workspace messaging system. It replaces the legacy workspace-bound channel architecture with a **user-centric topology**, introduces **strict message ordering** via a seq-based ledger, and uses a **multi-store data architecture** (PostgreSQL + DynamoDB + Redis + S3) designed to scale to millions of messages.

The new system powers **human-to-human real-time messaging** — DMs, group chats, workspace team conversations, and thread-based discussions. It does **not** replace AI Chat, which remains in its own service.

---

## Why Rewrite?

| Legacy Problem | Chat v2 Solution |
|----------------|------------------|
| Rooms were workspace-bound — DMs could not cross workspaces | User-centric topology: DMs are global, groups are independent, only Team Groups are workspace-tied |
| DynamoDB had no ordering guarantees — messages could arrive out of order | Per-room atomic seq counter ensures strict monotonic ordering |
| WebSocket connections were per-room — reconnection required full reload | Single global WebSocket with delta sync via seq numbers |
| Message list rendered all items in DOM — poor performance at scale | Virtualized list via `@tanstack/react-virtual` — only visible items rendered |
| Zustand store was monolithic — any update re-rendered entire tree | 5 micro-stores with Map-based O(1) lookups, shallow selectors |
| No thread support | Thread replies stored in DynamoDB with type discriminator, rendered in side panel |

---

## Topology at a Glance

```
User
├── Direct Messages       — global, not tied to any workspace
├── Groups                — user-created, public or private, independent
├── Workspace Team Group  — ONE per workspace, auto-created, membership
│                           auto-syncs with workspace membership
├── AI Chats              — isolated, handled by FastAPI AI service
└── Archived Chats        — any room type moved to archive
```

### Key Behavioral Rules

- Creating a workspace automatically provisions exactly one `WORKSPACE_TEAM` room
- Joining a workspace = joining its team group (Django signal)
- Leaving a workspace = leaving its team group (Django signal)
- Deleting a workspace archives its team group (soft-delete)
- DMs are global: the same pair of users share one room regardless of workspace
- Groups are sovereign: no parent workspace, created by any user
- **No sub-channels.** Every room is flat.

---

## Data Store Strategy

| Store | Holds | Why |
|-------|-------|-----|
| **PostgreSQL** | Room metadata, members, roles, permissions, pins, drafts, invites, unread counters | Relational queries, ACID transactions, joins |
| **DynamoDB** (single table) | Messages, thread replies, reactions, edits, read receipts, mentions, polls, voice notes, emoji reactions | Infinite write scaling, cursor pagination, no relational bloat |
| **Redis** | Presence, typing indicators, voice sessions, socket rooms, read cache | TTL-based expiry, sub-millisecond reads, Pub/Sub broadcast |
| **S3** | Images, videos, PDFs, files, voice recordings, screen recordings | Purpose-built for binary blobs, CDN delivery, cost-effective |

This follows how large-scale collaboration platforms are structured: business data in a relational store, high-volume append-only events in NoSQL, ephemeral state in Redis, assets in object storage.

---

## How Messages Are Ordered

Every room has a **monotonic seq counter** stored in DynamoDB:

```
room: "0194f8c2-..."
  └── counter item: { room_id, sort_key: "_counter", next_seq: 42 }
```

When a message is sent:
1. Atomically increment the counter via DynamoDB `UpdateItem ADD`
2. Use the returned value as the message's seq
3. Store the message with sort key `MSG#{seq:020d}`

This guarantees strict ordering — two concurrent sends always get different seq numbers. Zero-padding ensures lexicographic sort order matches numeric order.

---

## How Real-Time Works

### Connection Model (Changed)

| Legacy | Chat v2 |
|--------|---------|
| One WebSocket per room | Single global WebSocket per user |
| Reconnection = reload all messages | Reconnection = `SYNC_ROOMS` with last seen seqs |

### Protocol

```
Client connects → receives CONNECTED with all room summaries
Client SUBSCRIBES to a room → receives SYNC delta since last_seen_seq
Client SENDS → server allocates seq → stores → broadcasts to room group
```

### Reconnection Flow

```
WebSocket drops → client reconnects → emits SYNC_ROOMS
  └─ { room_id: "abc", last_seen_seq: 42 }
  └─ { room_id: "def", last_seen_seq: 17 }

Server responds with SYNC events:
  └─ { room_id: "abc", messages: [seq 43, 44, 45], upto_seq: 45 }
  └─ { room_id: "def", messages: [seq 18], upto_seq: 18 }
```

No HTTP fallback needed. The catch-up is pure delta.

---

## Frontend State Architecture

The monolithic Zustand store is split into 5 micro-stores:

| Store | State Shape | Persisted |
|-------|-------------|-----------|
| `messageStore` | `Record<roomId, Map<seq, Message>>` | No (in-memory) |
| `presenceStore` | `Record<userId, { status, lastActive }>` | No |
| `typingStore` | `Record<roomId, Set<userId>>` | No |
| `chatStore` | `activeRoomId, unreadByRoom, layout` | Yes (localStorage) |
| `uploadStore` | `Record<fileId, { progress, status }>` | No |

- Messages are stored in a `Map<seq, Message>` for O(1) insert/update/delete
- Components use shallow selectors — only re-render when their slice changes
- Unread counts persist across page refreshes via `zustand/persist`

---

## Key Metrics Targets

| Metric | Target |
|--------|--------|
| Message send latency (P95) | < 200ms (server round-trip) |
| Reconnection sync (P95) | < 500ms for 200 missed messages |
| Virtualized list render | 60fps at 100k messages |
| Store update (single message) | O(1) insert, O(1) delete |
| Room sidebar render | Virtualized, 10k+ rooms |

---

## Related Documents

| Document | Description |
|----------|-------------|
| `CHAT_V2_SYSTEM_DESIGN.md` | Deep system design: data models, store selection, trade-offs |
| `CHAT_V2_ARCHITECTURE.md` | Architecture reference: components, layers, implementation specs |
| `CHAT_V2_WORKFLOW.md` | Step-by-step workflows for every operation |
