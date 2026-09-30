# Architecture

How a request actually travels through Kraivor, and which trust boundaries it
crosses. This document exists because the service topology is spread across
`docker-compose.yml`, two Django services, two FastAPI services, and an Nginx
gateway, with no single place describing the whole path.

## Service topology

| Service | Port | Stack | Owns |
|---------|------|-------|------|
| `identity` (`services/auth`) | 8001 | Django 5 + DRF | Auth, users, API keys, OAuth, profiles |
| `core` (`services/core`) | 8002 | Django 5 + DRF | Workspaces, projects, tasks, knowledge, repos, chat, search, notifications |
| `analysis` (`services/analysis`) | 8003 | FastAPI | Repo analysis, rule engine, scoring |
| `ai` (`services/ai`) | 8004 | FastAPI | Agent orchestration, RAG, LLM providers |
| `realtime` (`services/realtime`) | 8006 | Node.js | WebSocket fan-out, chat delivery, presence |
| `notifications` (`services/notifications`) | 8005 | FastAPI | **Not implemented — see its README** |

Supporting infrastructure: `postgres`, `redis`, `kafka`, `dynamodb-local`,
`mailhog`, `nginx`.

> `notifications` is listed here because it appears in the compose file, but
> every file under `services/notifications/app/` is 0 bytes. Notification
> behaviour actually lives in `core/apps/notifications/`. Do not go looking for
> it in the service of the same name.

## Request path

```
Browser
  │
  ▼
nginx (API gateway)  ── terminates TLS, routes by path prefix
  │
  │  Proxies /auth/* → identity, /core/* → core, /analysis/* → analysis, /ai/* → ai
  │  Proxies /ws/*   → realtime
  ▼
Django service (identity or core)
  │
  ├─ JWTAuthMiddleware verifies the RS256 bearer token
  │    └─ sets request.user_id (a UUID), NOT a Django auth user
  │
  ├─ DRF permission classes decide authorisation
  │    identity/core use apps.workspaces.permissions.IsAuthenticated
  │
  └─ View → Selector → Service → Model
```

### The `request.user_id` convention

There is no `django.contrib.auth` user object in `core`. The gateway-auth
middleware verifies the JWT and sets `request.user_id` to a raw UUID. Every
permission class and view reads `request.user_id`. If you write a new view and
reach for `request.user`, you will get nothing useful.

### Authorisation is workspace-scoped

Authentication (is this caller a real user?) and authorisation (may they touch
*this* workspace?) are separate steps, and the second one is easy to skip.

The canonical lookup is:

```python
from apps.workspaces.selectors import WorkspaceSelector

workspace = WorkspaceSelector.get_workspace_for_user(workspace_id, request.user_id)
if workspace is None:
    raise NotFound("Workspace not found.")
```

It accepts a UUID or a slug, filters on an active (`deleted_at IS NULL`)
membership row, and returns `None` for non-members. Returning `404` rather than
`403` avoids confirming that a workspace exists to someone who is not a member.

**Any view that takes a workspace identifier from the request must go through
this lookup.** Taking the id straight from a query parameter and passing it to a
service is an IDOR — see `services/core/apps/search/views.py`, which did exactly
that until it was fixed, with regression tests in `apps/search/tests/`.

The permission ladder in `apps/workspaces/permissions.py` is:

| Class | Requires |
|-------|----------|
| `IsAuthenticated` | any valid `request.user_id` |
| `IsWorkspaceMember` | membership row |
| `IsWorkspaceAdmin` | membership row with admin role |
| `IsWorkspaceOwner` | `workspace.owner_id` matches |

## The internal request channel

Some endpoints must be called by another service rather than by a user. Those
use a shared secret in a header instead of a JWT:

- Header: `X-Internal-Request`
- Value: `INTERNAL_REQUEST_TOKEN` (auth) / `INTERNAL_REQUEST_SECRET` (core)

**These are the same secret under two names.** Core previously read
`INTERNAL_REQUEST_SECRET`, which no `.env` file ever set, so the entire
gateway→core trust path was dead: every internal call was treated as
unauthenticated and rejected. Both services now read `INTERNAL_REQUEST_TOKEN`,
and both refuse to boot in production without it.

A caller holding this secret skips JWT verification entirely and asserts its own
`X-User-ID` / `X-Workspace-IDs` headers. It must never be exposed to a browser,
never sent from the frontend, and never committed.

### Endpoints reachable without user auth

Three endpoint groups are unauthenticated by design. Each has a different
guard, and each is a thing to re-check when touching that code:

| Endpoint | Guard |
|----------|-------|
| `apps/community/views/internal.py` | `hmac.compare_digest` against a shared token |
| `apps/repositories/github_app/views.py` | signed `state` parameter (GitHub App OAuth) |
| `core/settings/development.py` | **no guard at all** — see below |

### The development-settings footgun

`services/core/core/settings/development.py` sets:

```python
REST_FRAMEWORK = {"DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"]}
```

That disables authentication for *every* endpoint in the service. It now
raises at import if `APP_ENV` is `production` or `prod`, so pointing
`DJANGO_SETTINGS_MODULE` at the dev module in production fails immediately
instead of silently serving an unauthenticated API.

## Async and events

- **Celery** — background work: `core-worker`, `ai-worker`, plus `*-beat`
  schedulers. Broker is Redis; `analysis` and `ai` also publish to Kafka.
- **Kafka** — domain events between `analysis`, `ai`, and `core`. Consumers
  live in `core-consumer` and `apps/notifications/management/commands/consume_events.py`.
- **DynamoDB** — chat messages. Access is always via
  `apps/chat/dynamodb/repository.py`. Rooms are user-centric: `Room.workspace`
  is only set for `WORKSPACE_TEAM` rooms, while DM, GROUP, and AI_CHAT rooms
  have no workspace at all. **Room membership (`Room.v2_members`) is the
  authorisation boundary for chat — not `Room.workspace`.**

## Data ownership

Each service owns its database and no service queries another's tables
directly. Cross-service reads go over HTTP with the internal request channel
above. Author identity is denormalised by `identity` and copied into `core`.

## Where things live

| Concern | Path |
|---------|------|
| Auth middleware (core) | `services/core/core/middleware/jwt_auth.py` |
| Permission ladder | `services/core/apps/workspaces/permissions.py` |
| Workspace membership lookup | `services/core/apps/workspaces/selectors/workspace_selectors.py` |
| Workspaces, projects, chat, knowledge | `services/core/apps/` |
| Auth, users, profiles, OAuth | `services/auth/auth/`, `services/auth/apps/` |
| Frontend API client (token refresh) | `frontend/src/lib/api/client.ts` |
| AI provider metadata (single source) | `frontend/src/constants/ai-providers.ts` |
| Deploy pipeline | `.github/workflows/deploy.yml`, `infra/` |
