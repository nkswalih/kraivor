# Kraivor Core Service — Architecture & Design Document

> **Document Version:** 1.0
> **Last Updated:** 2026-06-02
> **Service:** Core Service (Django)
> **Status:** Proposed — pending architecture decisions
> **Classification:** Internal — Architecture

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Merged Service Strategy](#3-merged-service-strategy)
4. [Kafka Architecture](#4-kafka-architecture)
5. [Celery & Background Jobs](#5-celery--background-jobs)
6. [Django Channels & Real-Time Chat](#6-django-channels--real-time-chat)
7. [Notification Architecture](#7-notification-architecture)
8. [Redis Data Flow](#8-redis-data-flow)
9. [DynamoDB for Chat History](#9-dynamodb-for-chat-history)
10. [Database Architecture](#10-database-architecture)
11. [Event Catalog](#11-event-catalog)
12. [Data Flow Diagrams](#12-data-flow-diagrams)
13. [Data Store Decision Matrix](#13-data-store-decision-matrix)
14. [Free Tier Analysis](#14-free-tier-analysis)
15. [Folder Structure](#15-folder-structure)
16. [Docker Compose Integration](#16-docker-compose-integration)
17. [Testing Strategy](#17-testing-strategy)
18. [Migration Plan](#18-migration-plan)
19. [Open Questions](#19-open-questions)

---

## 1. Introduction

### What the Core Service Is

The Core Service is the central orchestration layer of the Kraivor platform. It manages workspace lifecycle, repository metadata, member management, real-time collaboration, and notification delivery. It is the service clients interact with most — every API call that is not authentication-related flows through Core.

In the **merged architecture**, Core also owns real-time WebSocket connections (via Django Channels) and notification delivery (via Celery + Kafka consumer). This replaces the previous architecture where notifications and realtime were separate microservices.

### Why Merge

| Factor | Separate Services | Merged into Core |
|---|---|---|
| Codebase complexity | 3 repos, 3 languages | 1 repo, 1 language (Python) |
| Deployment overhead | 3 Docker images, 3 health checks | 1 Docker image + workers |
| Inter-service latency | Network calls for every event | In-process, same DB |
| Developer iteration | Need to run 3 services locally | Run core + workers |
| Free tier viability | Requires managed Kafka, Redis | Minimal infra footprint |
| Learning curve | Need Django + FastAPI + Node.js | Django only |

### Scope of This Document

This document covers the proposed architecture for the merged Core service, focusing on:

- How Kafka, Celery, Django Channels, Redis, and DynamoDB integrate into Core
- Where each data store is used and why
- Notification lifecycle and storage decisions
- Real-time chat system design for AI bot + team collaboration
- Free tier constraints and trade-offs

---

## 2. High-Level Architecture

### System Overview

Core is a Django 5 application with Django REST Framework (DRF) for HTTP APIs, Django Channels for WebSocket, Celery for async workers, and an embedded Kafka consumer for event processing.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE SERVICE                                     │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                         Django ASGI Application                          │  │
│  │                                                                          │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │  │
│  │  │   HTTP API       │  │   WebSocket     │  │   Admin / Health        │  │  │
│  │  │   (DRF views)    │  │   (Channels)    │  │   (Django原生)          │  │  │
│  │  └────────┬────────┘  └────────┬────────┘  └─────────────────────────┘  │  │
│  │           │                     │                                         │  │
│  │  ┌────────▼─────────────────────▼─────────────────────────────────────┐  │  │
│  │  │                    URL Routing (ProtocolTypeRouter)                 │  │  │
│  │  │  /api/* → HTTP   │  ws/chat/* → ChatConsumer  │  ws/notify/* → ...│  │  │
│  │  └────────────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────┐  │
│  │  Celery Workers   │  │  Celery Beat     │  │  Kafka Consumer (mgmt cmd) │  │
│  │  - Email delivery  │  │  - Scheduled     │  │  - Listens to workspace   │  │
│  │  - Push notif.    │  │    cleanup       │  │    events, repository      │  │
│  │  - In-app notif.  │  │  - Digest gen    │  │    events, analysis events │  │
│  │                   │  │  - TTL sweep     │  │  - Dispatches Celery tasks │  │
│  └──────────────────┘  └──────────────────┘  └────────────────────────────┘  │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                       Infrastructure Layer                               │  │
│  │  Kafka Producer │ Kafka Consumer │ Redis Client │ DynamoDB Client        │  │
│  │  Firebase Admin  │ SMTP Client   │ Channel Layer                          │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Process Model

| Process | Command | Purpose |
|---|---|---|
| Django ASGI (uvicorn) | `uvicorn core.asgi:application` | HTTP API + WebSocket |
| Celery Worker | `celery -A core.celery_app worker -Q notifications,default` | Background tasks |
| Celery Beat | `celery -A core.celery_app beat` | Scheduled tasks |
| Kafka Consumer | `python manage.py consume_events` | Event → Task dispatch |

---

## 3. Merged Service Strategy

### What Is Merged

The following services are consolidated into Core:

| Previous Service | Now Part of Core | Rationale |
|---|---|---|
| **Notification Service** (FastAPI) | Celery tasks + management commands | Notifications are triggered by Core events; in-process dispatch removes network hop |
| **Realtime Service** (Node.js + Socket.io) | Django Channels + Redis layer | WebSocket in Django eliminates cross-service state sync; one connection protocol |
| **Kafka Consumer** (external) | Django management command | Single event loop inside Core; uses existing Celery for dispatch |

### What Stays Separate

| Service | Reason |
|---|---|
| **Identity Service** (Auth) | Security boundary — separation of auth from business logic |
| **Analysis Service** | CPU-intensive, needs independent scaling |
| **AI Service** | LLM calls are I/O-bound, needs independent scaling |
| **Frontend** (Next.js) | Client-side rendering, different runtime |

### Boundary Definition

Core communicates with other services exclusively through:

1. **HTTP REST** (internal, behind API Gateway) — synchronous queries
2. **Kafka events** — asynchronous notifications (analysis.completed, ai.index.completed)
3. **X-Internal-Request header** — service-to-service authentication

Core never accesses another service's database directly. Other services never access Core's database directly.

---

## 4. Kafka Architecture

### Role of Kafka in Core

Kafka is the event backbone. Core uses it for two distinct purposes:

1. **Publishing domain events** — Core publishes events when domain entities change (repository connected, workspace created, member invited)
2. **Consuming downstream events** — Core consumes events from Analysis and AI services to trigger notifications and real-time updates

### Publisher Pattern

Every Core app that owns domain state has an `events.py` with a publisher class:

```
apps/
  workspaces/
    events.py   → WorkspaceEventPublisher (topic: workspace.events)
  repositories/
    events.py   → RepositoryEventPublisher (topic: repository.events)
  chat/         → ChatEventPublisher (topic: chat.events)
  notifications/
    events.py   → NotificationEventPublisher (topic: notification.events)
```

Publisher contract:
- Events are **fire-and-forget** — failure never rolls back the DB transaction
- Publishing is registered via `transaction.on_commit()` — only fires after DB commit
- In dev (no Kafka), events fall back to structured logging
- Events follow the standard platform envelope:

```json
{
  "event_id": "uuid-v4",
  "event_type": "repository.connected",
  "source_service": "core",
  "workspace_id": "uuid",
  "user_id": "uuid",
  "timestamp": "ISO-8601",
  "version": "1.0",
  "data": { }
}
```

### Producer Infrastructure

**`core/infrastructure/kafka.py`** — singleton producer pool:

```python
# Pseudocode
_producer = None

def get_producer():
    global _producer
    if _producer is None:
        conf = {
            "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "core-producer",
            "acks": "all",
            "compression.type": "snappy",
        }
        _producer = Producer(conf)
    return _producer
```

Settings loaded from environment:

| Variable | Default | Description |
|---|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka broker address |
| `KAFKA_FLUSH_TIMEOUT` | `2.0` | Max seconds to wait for producer flush |
| `KAFKA_CONSUMER_GROUP` | `core-consumer` | Consumer group for event consumption |
| `KAFKA_AUTO_CREATE_TOPICS` | `True` | Auto-create topics in dev |

### Consumer Architecture

The Kafka consumer runs as a Django management command:

**`python manage.py consume_events`** — long-running process that:

1. Subscribes to topics: `analysis.events`, `ai.events`, `chat.events`
2. Deserializes the event envelope
3. Routes to handler functions based on `event_type`
4. Handlers dispatch Celery tasks (send email, push notification, broadcast to channels)

This is a separate OS process (scalable independently), not a thread inside the ASGI server.

```
Kafka Topics
    │
    ▼
consume_events (management command)
    │
    ├── analysis.completed ──► Celery: notify_analysis_completed
    ├── analysis.failed    ──► Celery: notify_analysis_failed
    ├── ai.index.completed ──► Celery: notify_index_completed
    └── chat.message.sent  ──► Celery: persist_message_to_dynamodb
```

### Graceful Degradation

| Kafka State | Core Behavior |
|---|---|
| Kafka running | Events published and consumed normally |
| Kafka down (producer) | `transaction.on_commit` fires, `_publish()` logs warning, event is lost — business operation succeeds |
| Kafka down (consumer) | Management command exits with error; events queue up in Kafka; replay on restart |
| No Kafka configured (dev) | Producers log events to stdout; consumer command is not started |

---

## 5. Celery & Background Jobs

### Where Celery Is Used

Celery is the async task engine for all operations that cannot complete within an HTTP request lifecycle (>500ms rule).

| Task Category | Queue | Examples |
|---|---|---|
| **Email delivery** | `notifications` | Send invitation email, password reset, digest |
| **Push notifications** | `notifications` | Firebase push for chat mentions, analysis complete |
| **In-app notifications** | `notifications` | Store notification in Redis feed, broadcast via Channels |
| **Data persistence** | `default` | Write chat message to DynamoDB, update analytics |
| **Cleanup jobs** | `default` | Soft-delete expired notifications, sweep stale presence |
| **External API calls** | `default` | Fetch GitHub metadata refresh, webhook dispatch |

### Celery App Instance

**`core/celery_app.py`**:

```python
from celery import Celery

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

### Task Routing

```python
# settings/base.py
CELERY_TASK_ROUTES = {
    "workspaces.tasks.*": {"queue": "notifications"},
    "notifications.tasks.*": {"queue": "notifications"},
    "chat.tasks.*": {"queue": "default"},
}
```

### Celery Beat Schedule

Built-in periodic tasks defined in settings:

| Task | Schedule | Queue | Purpose |
|---|---|---|---|
| `cleanup_expired_notifications` | Every hour | `default` | Hard-delete expired soft-delete notifications from Postgres |
| `sweep_stale_presence` | Every 5 min | `default` | Clean up stale Redis presence keys |
| `send_daily_digest` | Every 24h at 8am | `notifications` | Daily notification digest (future) |

### Idempotency & Retry Design

Every Celery task follows these rules:
- Accepts primitive args only (strings, ints, UUIDs as str) — never model instances
- Queries the DB itself to get current state
- Checks idempotency guards at the start (skip if already done)
- Uses exponential backoff: `countdown = 30 * (2 ** retries)`
- Logs outcome at INFO level

---

## 6. Django Channels & Real-Time Chat

### Why Django Channels Over Socket.io

| Factor | Django Channels | Separate Node.js Socket.io |
|---|---|---|
| Language consistency | Python throughout | Python + JavaScript |
| Authentication | Shares Django auth middleware | Needs separate JWT verification |
| Database access | Same ORM, same session | HTTP call to Core API |
| Deployment | One process type (uvicorn) | Separate Docker image |
| Free tier complexity | Minimal | Extra service to monitor |
| Community & maturity | Mature (Channels 4.x) | Mature (Socket.io 4.x) |

### ASGI Application Stack

```
┌─────────────────────────────────────────────────────┐
│               ProtocolTypeRouter                      │
│                                                       │
│  ChannelNameRouter                                    │
│  ├── "http" ──► DjangoASGIHandler (DRF + Admin)      │
│  │                                                     │
│  └── "websocket" ──► AuthMiddlewareStack               │
│                          │                              │
│                          ▼                              │
│                    URLRouter                            │
│                    ├── ws/chat/<room_id>/ ──► ChatConsumer │
│                    ├── ws/notifications/  ──► NotifConsumer│
│                    └── ws/presence/       ──► PresenceCons.│
└─────────────────────────────────────────────────────┘
```

### Channel Layer Backend

Redis is used as the **channel layer backend** for:

1. **Multi-instance broadcast** — When one Django instance sends a message, all instances deliver it to connected WebSocket clients
2. **Presence tracking** — Which users are online, which rooms they've joined
3. **Group management** — Send messages to all members of a workspace room

```python
# settings/base.py
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
            "capacity": 1500,
            "expiry": 60,
        },
    },
}
```

**Data loss tolerance**: The channel layer is ephemeral. If Redis restarts, in-flight WebSocket messages are lost — the client reconnects and receives state from the database (DynamoDB for chat) or API response.

### WebSocket Consumer Architecture

#### ChatConsumer (`ws/chat/{room_id}/`)

Handles real-time messaging between team members and the AI bot.

```python
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Verify user is workspace member (JWT from query string)
        # Join the Channels group for this room
        # Add user to Redis presence set for this room
        # Send recent message history from DynamoDB
        # Accept the connection

    async def disconnect(self):
        # Remove user from Redis presence set
        # Leave the Channels group
        # Broadcast presence update to room

    async def receive(self, text_data):
        # Parse message (text, image_ref, system_command)
        # If user message:
        #   Store in DynamoDB (async Celery task)
        #   Broadcast to room via group_send
        #   If mentions AI bot, trigger AI agent response
        # If system command:
        #   typing.start, typing.stop, mark_read, delete

    async def chat_message(self, event):
        # Receive broadcast from group_send
        # Send to WebSocket
```

#### NotificationConsumer (`ws/notifications/`)

Realtime push of in-app notifications to the connected user.

```python
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join user-specific group: notify_user_{user_id}
        # Accept

    async def receive(self, text_data):
        # Handle "mark_read", "mark_all_read", "dismiss"

    async def send_notification(self, event):
        # Forward notification payload to client
```

#### PresenceConsumer (`ws/presence/`)

Lightweight heartbeat endpoint for online status.

### Chat Room Types

| Room Type | Scope | Participants |
|---|---|---|
| **Workspace General** | `chat:workspace:{workspace_id}` | All workspace members |
| **Group Chat** | `chat:group:{group_id}` | Selected members |
| **AI Thread** | `chat:ai:{thread_id}` | User(s) + AI bot |
| **Direct Message** | `chat:dm:{user_a}:{user_b}` | Two users |

---

## 7. Notification Architecture

### Design Principles

1. **Ephemeral by default** — Notifications live in Redis with TTL. They are fast, disposable, and gone on logout.
2. **Save on demand** — If a user explicitly saves/bookmarks a notification, it persists to PostgreSQL.
3. **Auto-disappear** — Default TTL of 24 hours. User can set custom TTL per notification type.
4. **Logout = flush** — On logout, the client sends a request to clear the user's notification feed from Redis.
5. **No dual-write problem** — Write to Redis first (fast path). Save to PostgreSQL only when user explicitly acts.

### Notification Lifecycle

```
Event occurs (e.g., analysis completed)
    │
    ▼
Kafka event consumed by `consume_events` command
    │
    ▼
Celery task dispatched: `dispatch_notification`
    │
    ├── 1. Create notification payload
    │     {id, type, title, body, workspace_id, actor_id, link, ttl}
    │
    ├── 2. Write to Redis (fast path)
    │     Key: notif:{user_id}:{notification_id}
    │     Expire: TTL (default 24h, user-configurable)
    │     List: LPUSH notif:feed:{user_id} {notification_id}
    │
    ├── 3. Broadcast via Channels
    │     group_send("notify_user_{user_id}", {type: "send_notification", payload})
    │
    ├── 4. If push enabled: Firebase send (fire-and-forget)
    │
    └── 5. If user saves: persist to PostgreSQL Notification model
```

### Redis Data Structures for Notifications

```
# Notification payload (single notification)
Key:      notif:{user_id}:{notif_id}
Type:     HASH
Fields:   id, type, title, body, workspace_id, actor_id, link, created_at, read_at, ttl
TTL:      86400 (24h) or custom

# Notification feed (ordered list of notification IDs per user)
Key:      notif:feed:{user_id}
Type:     LIST (sorted by recency)
Values:   notification_id strings
TTL:      None (managed per-item)
Ops:      LPUSH on new, LREM on delete/dismiss, LRANGE for pagination

# Read markers
Key:      notif:read:{user_id}:{notif_id}
Type:     STRING
Value:    timestamp ISO-8601
TTL:      Same as notification TTL

# User TTL preference (optional)
Key:      notif:pref:{user_id}:ttl
Type:     STRING
Value:    seconds (default: 86400)
```

### PostgreSQL Notification Model

Used only when user explicitly saves/archives a notification:

```python
class SavedNotification(TimestampedModel):
    """Persisted notification — created when user saves from Redis feed."""
    user = models.UUIDField(db_index=True)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, null=True)
    notification_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    body = models.TextField()
    link = models.URLField(max_length=500, blank=True)
    actor_id = models.UUIDField(null=True)
    read_at = models.DateTimeField(null=True)
    saved_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
```

### Push Notification via Firebase

Firebase Cloud Messaging (FCM) is used for push notifications. Firebase Spark plan is free:

| Firebase Free Tier | Limit |
|---|---|
| Cloud Messaging | Unlimited messages |
| Analytics | 1 analytics property |
| Crashlytics | Included |

Flow:
```
Celery task send_push_notification
    │
    ├── Query user's FCM tokens from PostgreSQL (FCMToken model)
    ├── Build notification payload (title, body, data)
    ├── Send via firebase-admin SDK
    └── Log delivery result
```

### Notification Channel Decision

| Channel | Technology | Free? | Use Case |
|---|---|---|---|
| In-app (feed) | Redis + Channels WebSocket | ✅ Yes | Real-time notification feed |
| Push (mobile) | Firebase Cloud Messaging | ✅ Yes (Spark plan) | Mobile push notifications |
| Email | Celery + SMTP / MailHog (dev) | ✅ Yes | Invitations, daily digest |
| Slack webhook | HTTP POST | ✅ Yes | Enterprise integration (future) |

**AWS Lambda + SQS are not needed** — Celery + Redis replaces both for free.

---

## 8. Redis Data Flow

### What Redis Is Used For

| Layer | Technology | Data | Ephemeral? |
|---|---|---|---|
| Celery broker | Redis | Task queue | ✅ Transient |
| Celery result backend | Redis | Task results (optional) | ✅ Configurable TTL |
| Channels layer | Redis | WebSocket group state | ✅ Ephemeral |
| Notification feed | Redis | Active notification payloads | ✅ TTL-based |
| Presence | Redis | Online status, heartbeat | ✅ 30s TTL |
| Cache (DRF) | Redis | API response cache | ✅ Configurable TTL |
| Rate limiting | Redis | Request counters | ✅ Sliding window |

### Data Loss Tolerance

| Data | If Redis Restarts | Mitigation |
|---|---|---|
| Celery tasks | Lost (re-queue from DB if not acked) | Tasks are idempotent |
| WebSocket state | Connections drop, clients reconnect | Client reconnects automatically |
| Notification feed | Lost — user sees empty feed | User refreshes, sees nothing (acceptable) |
| Presence data | All users appear offline | Heartbeat repopulates on next ping |
| Cache | Cold start — slightly slower queries | DB handles the load temporarily |

### Redis Persistence Configuration

For production, Redis AOF (Append-Only File) with `appendfsync everysec` provides durability with minimal performance impact. For development, no persistence is needed.

### Multi-Purpose Redis vs Separate Instances

For an indie developer on free tier, a single Redis instance for all purposes is acceptable. Redis handles thousands of operations per second on a single core. If traffic grows, separate Redis instances per concern is a production scaling step — not necessary at the start.

---

## 9. DynamoDB for Chat History

### Why DynamoDB for Chat

| Requirement | DynamoDB | PostgreSQL | Redis |
|---|---|---|---|
| Structured message history | ✅ Native | ✅ With schema | ❌ No queries |
| High-volume writes | ✅ Auto-scaling | ✅ With tuning | ✅ Fast but volatile |
| Pagination | ✅ Query with LastEvaluatedKey | ✅ LIMIT/OFFSET | ❌ LRANGE only |
| Sorting by time | ✅ SK as timestamp | ✅ ORDER BY | ❌ Manual |
| Free tier | ✅ 25GB, 25 RCU/WCU | ✅ Unlimited (self-hosted) | ✅ In-memory only |
| No schema migrations | ✅ Schemaless | ❌ Migrations required | ✅ No schema |

### Table Design

```
Table: kraivor-chat-messages
Region: us-east-1 (or local via DynamoDB Local)
Billing: PAY_PER_REQUEST (free tier: 25 RCU/WCU forever)

Primary Key:
  PK: room_id (String)    — Partition key, e.g. "workspace:abc123" or "dm:user1:user2"
  SK: message_id (String) — Sort key, "{timestamp_ms}:{uuid_v4_prefix}"

GSI:
  GSI1 - user_messages
    PK: sender_id (String)
    SK: created_at (String, ISO-8601)
    Purpose: Query all messages by a user

  GSI2 - room_by_activity (optional, for "my recent chats")
    PK: user_id (String)
    SK: last_activity (String, ISO-8601)
    Purpose: List rooms a user has activity in

Attributes (single document per message):
  room_id:         String          — Partition key
  message_id:      String          — Sort key
  sender_id:       String (UUID)
  sender_name:     String
  content:         String          — Message text (up to 64KB)
  content_type:    String          — "text", "image", "system", "ai_response"
  reply_to:        String (nullable) — message_id this replies to
  mentions:        List<String>    — user_ids mentioned
  attachment_url:  String (nullable)
  created_at:      String (ISO-8601)
  edited_at:       String (nullable)
  deleted_at:      String (nullable) — soft delete
```

### DynamoDB Client in Core

**`core/infrastructure/dynamodb.py`**:

```python
import boto3
from django.conf import settings

_client = None

def get_dynamodb():
    global _client
    if _client is None:
        if settings.DYNAMODB_LOCAL:
            _client = boto3.resource("dynamodb", endpoint_url="http://dynamodb-local:8000")
        else:
            _client = boto3.resource("dynamodb")
    return _client
```

### Local Development

[DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html) runs as a Docker container (free, no AWS account needed):

```yaml
# docker-compose.yml
dynamodb-local:
  image: amazon/dynamodb-local:latest
  container_name: kraivor-dynamodb
  ports:
    - "8007:8000"
  command: "-jar DynamoDBLocal.jar -sharedDb -dbPath /data"
  volumes:
    - dynamodb_data:/data
```

### Migration from DynamoDB to PostgreSQL (Future)

If DynamoDB free tier limits are hit, chat history can be migrated to PostgreSQL with a simple table:

```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    room_id UUID NOT NULL REFERENCES chat_rooms(id),
    sender_id UUID NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- ...
);
CREATE INDEX idx_chat_messages_room ON chat_messages(room_id, created_at DESC);
```

The `apps/chat/` service layer abstracts the data store behind a repository interface — switching from DynamoDB to PostgreSQL means changing one implementation class, not rewriting consumers.

---

## 10. Database Architecture

### Data Store Per Concern

| Concern | Primary Store | Cache/Index | Rationale |
|---|---|---|---|
| Workspace metadata | PostgreSQL | Redis (read cache) | Relational, transactional |
| Repository metadata | PostgreSQL | — | Relational, few writes |
| Member management | PostgreSQL | Redis (presence) | Relational, transactional |
| Chat messages | **DynamoDB** | — | High-volume writes, paginated reads |
| Chat rooms | PostgreSQL | Redis (members) | Room metadata is relational |
| Notifications (active) | **Redis** | — | Ephemeral, TTL-based |
| Notifications (saved) | **PostgreSQL** | — | Persistent, user-controlled |
| AI bot conversation state | Redis | — | Ephemeral, TTL-based |
| User sessions | Redis (auth) | — | Managed by Identity service |
| API response cache | Redis | — | Optional, TTL-based |

### PostgreSQL Tables (Core-Only)

```
modules/                    (future — project management)
```

### Chat Room Model (PostgreSQL)

Even though messages are in DynamoDB, chat room metadata is relational:

```python
class ChatRoom(TimestampedModel):
    workspace = ForeignKey(Workspace, on_delete=models.CASCADE, related_name="chat_rooms")
    name = CharField(max_length=255)
    room_type = CharField(max_length=20, choices=["workspace", "group", "ai", "dm"])
    created_by = UUIDField()
    is_active = BooleanField(default=True)
    # Metadata stored in PostgreSQL; messages stored in DynamoDB
```

---

## 11. Event Catalog

### Events Published by Core

| Event | Source | Payload Highlights | Consumers |
|---|---|---|---|
| `workspace.created` | workspaces | workspace_id, name, slug, plan | Notification → welcome |
| `workspace.deleted` | workspaces | workspace_id | Analysis, AI → cleanup |
| `workspace.member.invited` | workspaces | email, role, inviter | Notification → email |
| `workspace.member.joined` | workspaces | user_id, role | Notification → broadcast |
| `workspace.member.role_changed` | workspaces | user_id, old_role, new_role | Notification |
| `workspace.member.removed` | workspaces | user_id, reason | Notification → email |
| `repository.connected` | repositories | repo_id, github_repo, github_id | Analysis → scan; AI → index |
| `repository.disconnected` | repositories | repo_id, github_repo | Analysis → cancel jobs; AI → remove embeddings |
| `chat.message.sent` | chat | room_id, sender_id, content_preview | Realtime → broadcast |

### Events Consumed by Core

| Event | Source | Handler Action |
|---|---|---|
| `analysis.completed` | Analysis | Send notification, update repo.last_analyzed_at |
| `analysis.failed` | Analysis | Send notification with error details |
| `ai.index.completed` | AI | Set repo.indexed = True |
| `ai.analysis.completed` | AI | Store AI report, send notification |
| `user.deleted` | Identity | Clean up workspace memberships |

---

## 12. Data Flow Diagrams

### Flow 1 — Chat Message (Team Member to Room)

```
User A sends message via WebSocket
    │
    ▼
ChatConsumer.receive()
    │
    ├── Validate (JWT, workspace membership)
    ├── Create message payload
    ├── Broadcast to room group (Channels → Redis → all connected instances)
    │
    ├── Fire-and-forget Celery task: persist_to_dynamodb
    │     └── Writes to DynamoDB table (room_id, message_id, content...)
    │
    └── If @mentions AI bot:
          └── Celery task: trigger_ai_response
                └── AI Service HTTP call → response streamed via SSE or WebSocket
```

### Flow 2 — Notification Delivery

```
Analysis completes → publishes analysis.completed to Kafka
    │
    ▼
consume_events (management command)
    │
    ▼
Dispatcher → Celery task: dispatch_notification
    │
    ├── 1. LPUSH to Redis: notif:feed:{user_id}
    ├── 2. SETEX to Redis: notif:{user_id}:{notif_id} (TTL 24h)
    ├── 3. Channels group_send to notify_user_{user_id} (if connected)
    ├── 4. If push enabled: Firebase send
    └── 5. Done
```

### Flow 3 — User Logout (Notification Cleanup)

```
Client sends POST /api/auth/logout (to Identity service)
    │
    ▼
Identity service publishes user.logged_out
    │
    ▼
Kafka consumer → Core Clears notification feed
    │
    ▼
DELETE notif:feed:{user_id}
DELETE notif:{user_id}:* (scan + del)
DELETE notif:read:{user_id}:*
```

### Flow 4 — User Saves a Notification

```
User clicks "Save" on notification in frontend
    │
    ▼
POST /api/notifications/{notif_id}/save/
    │
    ▼
View → reads from Redis
    │
    ▼
Creates SavedNotification in PostgreSQL
    │
    ▼
Removes TTL from Redis notification (or keeps it with extended TTL)
```

---

## 13. Data Store Decision Matrix

### Notifications — Redis vs PostgreSQL vs Others

| Factor | Redis | PostgreSQL | SQLite | DynamoDB |
|---|---|---|---|---|
| **Ephemeral (24h TTL)** | ✅ Native TTL | ⚠️ Requires cron job | ⚠️ Requires cron | ⚠️ Requires TTL attribute |
| **Gone on logout** | ✅ FLUSH/UNLINK | ❌ Must delete rows | ❌ Must delete rows | ❌ Must delete items |
| **User-deletable** | ✅ LREM/DEL | ✅ DELETE row | ✅ DELETE row | ✅ DeleteItem |
| **Disappearing (custom TTL)** | ✅ Per-key TTL | ⚠️ Requires field + sweep | ⚠️ Requires field + sweep | ✅ Native TTL |
| **Save long-term** | ❌ No persistence | ✅ NATIVE | ✅ Native | ✅ Native |
| **Fast read (real-time)** | ✅ <1ms | ⚠️ 5-20ms | ⚠️ File I/O | ⚠️ 5-15ms |
| **Free tier** | ✅ Already running | ✅ Already running | ✅ File-based | ✅ 25GB |
| **Operational complexity** | ✅ Minimal | ✅ Minimal | ✅ Minimal | ⚠️ Needs AWS/Docker Local |

**Verdict**: Redis for active feed (ephemeral) + PostgreSQL for saved notifications. This covers every requirement without adding new infrastructure.

### Chat — DynamoDB vs PostgreSQL vs MongoDB

| Factor | DynamoDB | PostgreSQL | MongoDB Atlas Free |
|---|---|---|---|
| **Free tier** | ✅ 25GB, 25 RCU/WCU | ✅ Unlimited (self-hosted) | ✅ 512MB |
| **Write throughput** | ✅ Auto-scales | ⚠️ Needs tuning | ⚠️ 100 ops/s |
| **Chat pagination** | ✅ Query + LastEvaluatedKey | ✅ LIMIT/OFFSET | ✅ Cursor-based |
| **Message ordering** | ✅ SK as timestamp | ✅ ORDER BY | ✅ Native |
| **Local dev** | ✅ DynamoDB Local (Docker) | ✅ Native | ❌ Needs Atlas cluster |
| **Serverless** | ✅ On-demand capacity | ❌ Needs EC2/RDS | ✅ Atlas serverless |
| **Time-to-live** | ✅ Native TTL | ⚠️ Cron | ✅ Native |
| **Full-text search** | ❌ Limited | ✅ Full | ✅ Text indexes |
| **AI bot integration** | ⚠️ Via app code | ✅ Via app code | ✅ Via app code |
| **Schema flexibility** | ✅ Schemaless | ❌ Fixed schema (migrations) | ✅ Schemaless |

**Verdict**: DynamoDB for chat history (per user's choice). PostgreSQL fallback if DynamoDB limits are hit. The service layer abstracts the storage behind an interface.

---

## 14. Free Tier Analysis

### Monthly Cost at Zero

| Service | Free Tier | What Kraivor Uses |
|---|---|---|
| PostgreSQL | ✅ Self-hosted Docker | All relational data |
| Redis | ✅ Self-hosted Docker | Cache, broker, channels, notifications |
| Kafka | ✅ Self-hosted Docker | Event bus |
| DynamoDB | ✅ 25GB / 25 RCU/WCU (forever) | Chat messages |
| Firebase | ✅ Spark plan (unlimited FCM) | Push notifications |
| DynamoDB Local | ✅ Free Docker image | Local development |
| S3 (optional) | ✅ 5GB (12 months) | File uploads, avatars |
| Pinecone (optional) | ✅ 1 free index | Vector embeddings (AI service) |
| MailHog | ✅ Free Docker image | Dev email capture |

**Total infrastructure cost for indie developer: $0/month** (self-hosted on a single machine or cheap VPS).

### When You Might Pay

| Threshold | Cost Trigger | Estimated Cost |
|---|---|---|
| >25GB chat history | DynamoDB paid tier | ~$1-2/GB/month |
| >1M Firebase pushes | Firebase Spark → Blaze | Pay per message (~$0.0001/msg) |
| Need managed Kafka | MSK or Confluent Cloud | ~$30-50/month minimum |
| Need managed Postgres | RDS or similar | ~$15/month minimum |

For an indie developer building an MVP, none of these thresholds will be hit for a long time.

---

## 15. Folder Structure

```
services/core/
├── core/
│   ├── __init__.py
│   ├── asgi.py                          # ASGI app — Channels + HTTP
│   ├── wsgi.py                          # WSGI app (for admin, fallback)
│   ├── urls.py                          # Root URL configuration
│   ├── celery_app.py                    # Celery app instance
│   ├── middleware/
│   │   └── jwt_auth.py                  # JWT verification middleware
│   └── settings/
│       ├── base.py                      # Shared settings (all envs)
│       ├── development.py               # Dev overrides
│       ├── production.py                # Prod overrides
│       └── test.py                      # Test overrides
│
├── apps/
│   ├── workspaces/                      # Workspace CRUD + members (KRV-019/020)
│   │   ├── models.py, views.py, serializers.py, services.py
│   │   ├── events.py, tasks.py, permissions.py
│   │   ├── urls.py, constants.py
│   │   ├── migrations/
│   │   └── tests/
│   │
│   ├── repositories/                    # Repository metadata (KRV-021)
│   │   ├── models.py, views.py, serializers.py, services.py
│   │   ├── events.py
│   │   ├── urls.py
│   │   ├── migrations/
│   │   └── tests/
│   │
│   ├── chat/                            # Real-time chat (proposed)
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── consumers.py                 # ChatConsumer, NotificationConsumer
│   │   ├── routing.py                   # WebSocket URL routing
│   │   ├── dynamodb.py                  # DynamoDB chat storage client
│   │   ├── models.py                    # ChatRoom (PostgreSQL)
│   │   ├── serializers.py
│   │   ├── tasks.py                     # persist_to_dynamodb, etc.
│   │   ├── migrations/
│   │   └── tests/
│   │
│   └── notifications/                   # Notification system (proposed)
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py                    # SavedNotification, FCMToken
│       ├── tasks.py                     # dispatch, push, email
│       ├── redis.py                     # Redis notification helpers
│       ├── firebase.py                  # Firebase Admin SDK wrapper
│       ├── management/
│       │   └── commands/
│       │       └── consume_events.py    # Kafka consumer entry point
│       ├── templates/
│       │   └── notifications/
│       │       └── email/              # Email templates
│       ├── migrations/
│       └── tests/
│
├── infrastructure/                      (proposed — to be created)
│   ├── __init__.py
│   ├── kafka.py                         # Kafka producer singleton
│   ├── redis.py                         # Redis client helpers
│   └── dynamodb.py                      # DynamoDB client helpers
│
├── tests/                               # Service-level tests
│   ├── conftest.py
│   ├── factories/
│   └── fixtures/
│
├── Dockerfile
├── Dockerfile.dev
├── pyproject.toml
├── manage.py
└── pytest.ini
```

---

## 16. Docker Compose Integration

### Proposed docker-compose services

```yaml
# docker-compose.yml (core sections)
services:
  # ... postgres, redis, kafka, identity, analysis, ai, frontend, nginx ...

  core:
    build: ./services/core
    container_name: kraivor-core
    command: uvicorn core.asgi:application --host 0.0.0.0 --port 8002 --reload
    env_file: .env
    environment:
      DATABASE_URL: postgres://kraivor:kraivor@postgres:5432/kraivor
      REDIS_HOST: redis
      KAFKA_BOOTSTRAP_SERVERS: kafka:9094
      DYNAMODB_LOCAL: "true"
      DYNAMODB_ENDPOINT: http://dynamodb-local:8000
    depends_on: [postgres, redis, kafka, dynamodb-local]
    ports: ["8002:8002"]

  core-worker:
    build: ./services/core
    container_name: kraivor-core-worker
    command: celery -A core.celery_app worker --loglevel=info
    env_file: .env
    environment:
      DATABASE_URL: postgres://kraivor:kraivor@postgres:5432/kraivor
      REDIS_HOST: redis
      KAFKA_BOOTSTRAP_SERVERS: kafka:9094
    depends_on: [postgres, redis, kafka]

  core-beat:
    build: ./services/core
    container_name: kraivor-core-beat
    command: celery -A core.celery_app beat --loglevel=info
    env_file: .env
    depends_on: [postgres, redis, kafka]

  core-consumer:
    build: ./services/core
    container_name: kraivor-core-consumer
    command: python manage.py consume_events
    env_file: .env
    depends_on: [postgres, redis, kafka]

  dynamodb-local:
    image: amazon/dynamodb-local:latest
    container_name: kraivor-dynamodb
    ports: ["8007:8000"]
    command: "-jar DynamoDBLocal.jar -sharedDb -dbPath /data"
    volumes:
      - dynamodb_data:/data

  # REMOVED: notifications (merged into core)
  # REMOVED: realtime (merged into core as Channels)
```

### Dev vs Prod Differences

| Aspect | Dev (docker-compose) | Production |
|---|---|---|
| Kafka | Bitnami container | Managed Kafka (MSK / Confluent) |
| DynamoDB | DynamoDB Local container | AWS DynamoDB (on-demand) |
| Firebase | No real push — log only | Real Firebase project |
| Email | MailHog (captures all) | SES / SendGrid |
| Core workers | Single worker process | Scaled with KEDA |

---

## 17. Testing Strategy

### Test Layers

| Layer | Tool | What It Tests |
|---|---|---|
| Unit (models) | pytest | Field defaults, validators, soft delete |
| Serializer | pytest | Input validation, output shape |
| Service | pytest + mock | Business logic, event publishing, external calls |
| View/HTTP | pytest-django + DRF test client | HTTP responses, status codes, permissions |
| Channels | pytest + channels test client | WebSocket connect/disconnect/send |
| Celery tasks | pytest with `CELERY_TASK_ALWAYS_EAGER` | Task logic, retry behavior |
| Kafka events | pytest with mock producer | Event publishing, envelope format |
| DynamoDB | moto (mock AWS) | Table operations, queries |

### Test Fixtures

Shared fixtures in `services/core/tests/conftest.py`:

```python
# Existing (already in place)
pytest_plugins = [
    "apps.workspaces.tests.fixtures",
    "apps.repositories.tests.fixtures",
]

# To add
@pytest.fixture
def mock_kafka_producer():
    with patch("core.infrastructure.kafka.get_producer") as mock:
        yield mock

@pytest.fixture
def mock_dynamodb():
    with mock_dynamodb():
        yield

@pytest.fixture
def channel_layer():
    # Use in-memory channel layer for tests
    ...
```

### Kafka Testing Strategy

- **Unit tests**: Mock `get_producer()` and assert `.produce()` was called with expected topic and payload
- **Integration tests**: A test Kafka container (via testcontainers-python or tox) would verify serialization — optional for MVP
- **Consumer tests**: Directly call the handler function with a sample event; assert the correct Celery task was dispatched

---

## 18. Migration Plan

### Phase 1 — Current State (Complete)
- [x] Workspace CRUD (KRV-019)
- [x] Member management (KRV-020)
- [x] Repository metadata (KRV-021) — code complete, needs migrations

### Phase 2 — Infrastructure (Next)
- [ ] Create `core/infrastructure/kafka.py` — producer singleton
- [ ] Create `core/celery_app.py` — Celery app instance
- [ ] Add Celery + Kafka settings to `base.py`
- [ ] Run `makemigrations repositories` → create `0001_initial.py`
- [ ] Add `confluent-kafka` to `pyproject.toml`

### Phase 3 — Notifications
- [ ] Create `apps/notifications/` app
- [ ] Implement Redis notification feed helpers
- [ ] Implement `dispatch_notification` Celery task
- [ ] Create `consume_events` management command
- [ ] Create `SavedNotification` model + save endpoint
- [ ] Integrate Firebase Admin SDK

### Phase 4 — Real-Time Chat
- [ ] Add `channels`, `channels-redis`, `boto3` to `pyproject.toml`
- [ ] Create `core/asgi.py` with ProtocolTypeRouter
- [ ] Create `apps/chat/` app
- [ ] Implement `ChatConsumer` (WebSocket handler)
- [ ] Implement `NotificationConsumer` (WebSocket handler)
- [ ] Create DynamoDB table + client
- [ ] Create `persist_to_dynamodb` Celery task
- [ ] Create `ChatRoom` model in PostgreSQL

### Phase 5 — Docker & Deployment
- [ ] Add DynamoDB Local to docker-compose
- [ ] Add core-worker, core-beat, core-consumer services
- [ ] Remove notifications and realtime service definitions
- [ ] Update nginx config for WebSocket routing
- [ ] Update kubernetes manifests

---

## 19. Open Questions

These decisions need to be made before implementation begins:

| Question | Options | Recommendation |
|---|---|---|
| **DynamoDB vs DragonflyDB for chat** | DynamoDB (free 25GB) vs DragonflyDB (Redis-compatible, 4GB free) vs PostgreSQL | DynamoDB — your choice, free tier is generous |
| **Firebase vs OneSignal for push** | Firebase (Spark free) vs OneSignal (10k subscribers free) vs custom | Firebase — better integration with Android/iOS |
| **Kafka vs RabbitMQ for events** | Kafka (current) vs RabbitMQ vs Redis pub/sub | Keep Kafka — already in docker-compose, events.py written for it |
| **Channels vs custom WSGI server** | Django Channels + Redis vs FastAPI behind Django | Channels — Django-native, ASGI support is mature |
| **LLM for AI chat bot** | OpenAI vs Anthropic vs local (Ollama) | Decoupled — AI service handles this, Core just calls it |
| **DynamoDB Local vs AWS free tier for dev** | Docker Local (no AWS needed) vs real AWS account | DynamoDB Local — offline dev, no account needed |

---

*Core Service Architecture Document — Kraivor Platform v1.0 (Proposed)*
*This document reflects the merged architecture where notifications and realtime services are consolidated into the Core Django service.*
