# Kraivor Identity Service — Production Documentation

> **Document Version:** 1.0  
> **Last Updated:** 2026-05-20  
> **Service:** Identity Service (Auth)  
> **Maintainers:** Backend Platform Team  
> **Classification:** Internal — Architecture

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Authentication Philosophy](#3-authentication-philosophy)
4. [Complete Authentication Flow](#4-complete-authentication-flow)
5. [JWT Architecture](#5-jwt-architecture)
6. [Redis Architecture](#6-redis-architecture)
7. [API Key Authentication](#7-api-key-authentication)
8. [DRF Authentication Backend](#8-drf-authentication-backend)
9. [Multi-Tenant Security](#9-multi-tenant-security)
10. [OAuth Architecture](#10-oauth-architecture)
11. [Security Architecture](#11-security-architecture)
12. [Database Architecture](#12-database-architecture)
13. [Celery & Background Jobs](#13-celery--background-jobs)
14. [Docker & Kubernetes Integration](#14-docker--kubernetes-integration)
15. [CI/CD Integration](#15-cicd-integration)
16. [Monitoring & Observability](#16-monitoring--observability)
17. [Sequence Diagrams](#17-sequence-diagrams)
18. [Redis Data Flow](#18-redis-data-flow)
19. [Full Request Lifecycle](#19-full-request-lifecycle)
20. [Folder Structure](#20-folder-structure)
21. [Testing Strategy](#21-testing-strategy)
22. [Current Improvements Implemented](#22-current-improvements-implemented)
23. [Recommended Future Improvements](#23-recommended-future-improvements)
24. [Summary](#24-summary)

---

## 1. Introduction

### What the Identity Service Is

The Identity Service (also referred to as the Auth Service) is the central authentication and authorization pillar of the Kraivor platform. It is a Django REST Framework (DRF) microservice responsible for all identity-related operations, including user registration, authentication, session management, API key lifecycle management, and OAuth integration.

### Why It Exists

In a microservices architecture, identity management cannot be duplicated across services. Every service must trust a centralized authority to establish user identity, and the Identity Service serves as that authority. It provides:

- **Single Source of Truth:** All user credentials, sessions, and authentication state are managed in one place.
- **Security Centralization:** Security policies (password hashing, token validation, rate limiting) are implemented once and applied uniformly.
- **Audit Compliance:** All authentication events are logged for compliance and security analysis.
- **Scalable Identity:** The service is designed to handle authentication for all downstream services without them needing to implement auth logic.

### Responsibilities of the Service

The Identity Service owns the following responsibilities:

| Responsibility | Description |
|---|---|
| User Management | Registration, profile management, soft deletion |
| Authentication | Password-based login, OTP, OAuth |
| Token Management | JWT access tokens, refresh token rotation, session revocation |
| API Keys | Generation, scoping, expiration, revocation |
| Rate Limiting | Login attempt tracking, account lockout |
| Email Operations | Verification emails, transactional notifications |
| OAuth Integration | GitHub, Google, Apple identity providers |
| JWKS Distribution | Public key endpoint for service-to-service JWT verification |

---

## 2. High-Level Architecture

### System Overview

The Identity Service is built on Django 5 with Django REST Framework, running as a stateless API backed by PostgreSQL for persistent data and Redis for high-speed operations (session caching, rate limiting, lockout tracking).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                         │
│  Web App (Next.js)  │  Mobile App  │  CLI  │  CI/CD Pipelines  │  Services  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY (Kong/Nginx)                              │
│              JWT Verification  │  Rate Limiting  │  Routing                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     IDENTITY SERVICE (Django DRF)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Users App   │  │ Authentication│  │  API Keys    │  │   Common     │   │
│  │   - Models    │  │   - JWT       │  │   - Scopes   │  │  - Logging   │   │
│  │   - Views     │  │   - OAuth     │  │   - Hashing  │  │  - Middleware│   │
│  │   - Serializ. │  │   - OTP       │  │   - Backend  │  │  - Utils     │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    SERVICE LAYER (Selectors & Services)            │   │
│  │   token_service  │  api_key_service  │  oauth_service  │  user_service │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                           │
                    ▼                           ▼
         ┌──────────────────┐         ┌──────────────────┐
         │   PostgreSQL     │         │      Redis       │
         │  (Persistent)    │         │  (Ephemeral)     │
         │  - Users         │         │  - Rate Limits   │
         │  - Refresh Tokens│         │  - Lockout       │
         │  - API Keys      │         │  - Session Cache │
         │  - OAuth Links   │         │  - OTP Cache     │
         └──────────────────┘         └──────────────────┘
```

### How Django, DRF, PostgreSQL, Redis, Celery Work Together

**Django** serves as the web framework, providing the request/response cycle, ORM for database operations, and the application structure. It handles routing, middleware execution, and view processing.

**Django REST Framework (DRF)** extends Django with RESTful capabilities. It provides:
- Serializers for request/response transformation
- Authentication classes that verify credentials
- Permission classes that enforce authorization
- Viewsets and routers for CRUD operations

**PostgreSQL** is the system of record for all persistent data:
- User accounts and profiles
- Refresh token records (hashed)
- API key records (hashed)
- OAuth identity links
- Audit logs

**Redis** handles high-speed, ephemeral state:
- Login attempt tracking (failure counts)
- Account lockout state
- OTP storage and validation
- JWT blacklist for revocation
- Session metadata caching

**Celery** handles asynchronous operations:
- Email delivery (verification, password reset)
- OAuth token refresh
- Session cleanup jobs
- Rate limit analytics

### Microservice Communication

The Identity Service exposes a JWKS endpoint at `/.well-known/jwks.json` that other services use to verify JWT signatures without making HTTP calls to the Identity Service. This is critical for performance — JWT verification happens locally on each service using the cached public key.

For service-to-service communication (e.g., Core Service calling Identity Service to validate an API key), an internal header `X-Internal-Request` is used alongside a shared secret `INTERNAL_REQUEST_TOKEN`.

### Scalability Approach

The Identity Service is designed as a **stateless API** that can be horizontally scaled:

1. **Statelessness:** No session state is stored in the application; PostgreSQL and Redis provide the state.
2. **Database Connection Pooling:** PgBouncer sits between Django and PostgreSQL to multiplex connections.
3. **Redis Cluster:** For higher traffic, Redis can be clustered for horizontal scaling.
4. **Read Replicas:** Read-heavy operations (user lookups) can route to PostgreSQL read replicas.
5. **Celery Workers:** Background jobs scale independently from the API.

---

## 3. Authentication Philosophy

### Stateless Access Tokens

The Identity Service uses **JWT (JSON Web Tokens)** for access tokens — compact, URL-safe tokens that contain claims about the user. JWTs are **stateless**: the server does not need to store any session data; the token itself contains all necessary information, verified cryptographically.

**Advantages:**
- No database lookup on every request — significantly reduces latency
- Decoupled from storage — works across multiple service instances
- Portable — same token works across services, mobile, CLI

**Tradeoff:** JWTs cannot be revoked before expiration. If a token is compromised, you must wait for it to expire or implement a blacklist (handled via Redis in this implementation).

### Stateful Refresh/Session Layer

While access tokens are stateless, the **refresh token** layer is **stateful**. This is intentional — refresh tokens have long lifecycles (30 days) and must be revocable. Every refresh token is:

1. **Hashed** with SHA-256 and stored in PostgreSQL
2. **Tracked** with metadata (device_id, IP, user-agent, expiration)
3. **Rotated** on every use — old token is invalidated, new token issued
4. **Revocable** individually or in bulk

This stateful approach enables:
- Session listing (all active devices)
- Session revocation (logout from specific device)
- Replay attack detection (if a token is used twice, all sessions invalidated)
- Device-level security policies

### Security-First Architecture

Every design decision prioritizes security:

- **Asymmetric Keys (RS256):** Access tokens are signed with RSA private keys; public keys are distributed via JWKS.
- **Constant-Time Comparisons:** Passwords and API keys use `hmac.compare_digest` to prevent timing attacks.
- **Secure Cookies:** Refresh tokens use HttpOnly, Secure, SameSite=Strict cookies.
- **Rate Limiting:** Login attempts are rate-limited per email+IP combination.
- **Audit Logging:** Every authentication event is logged with structured data.
- **Soft Delete:** Users are never hard-deleted; data is retained for forensics.

### Why JWT + Redis Combination Is Used

| Layer | Technology | Purpose |
|---|---|---|
| Access Token | JWT (RS256) | Stateless authentication for API calls |
| Refresh Token | Database + Redis | Stateful session management, revocation |
| Rate Limiting | Redis | Fast, distributed lockout tracking |
| OTP | Redis | Short-lived, single-use codes |

This combination balances performance (JWT for speed) with security (stateful refresh for control).

---

## 4. Complete Authentication Flow

### Step-by-Step Login Flow

The Kraivor Identity Service implements a **multi-step sign-in** pattern (KRV-011), designed to optimize UX and security:

```
┌─────────┐                           ┌─────────────┐                    ┌──────────┐
│  Client │                           │ Identity Svc│                    │   Redis  │
└────┬────┘                           └──────┬──────┘                    └────┬─────┘
     │                                        │                               │
     │  1. POST /api/auth/signin/identify/    │                               │
     │     { "email": "user@example.com" }   │                               │
     ├──────────────────────────────────────►│                               │
     │                                        │  Check:                       │
     │                                        │  - User exists?              │
     │                                        │  - Email verified?          │
     │                                        │  - Locked out?              │
     │                                        ├─────────────────────────────►│
     │                                        │                               │ GET lockout
     │                                        │                               │
     │  2. Response: { "next_step": "choose_method", "methods": ["password", "otp"] }
     │◄───────────────────────────────────────┤                               │
     │                                        │                               │
     │  3a. POST /api/auth/signin/password/   │                               │
     │      { "email": "...", "password": "..." }                             │
     ├──────────────────────────────────────►│                               │
     │                                        │  Verify password:            │
     │                                        │  - check_password()         │
     │                                        │  - Record failure if wrong │
     │                                        ├─────────────────────────────►│ (if fail)
     │                                        │                               │ INCR fail
     │                                        │                               │ count
     │                                        │                               │
     │                                        │  If success:                │
     │                                        │  - Generate JWT pair        │
     │                                        │  - Store refresh token hash │
     │                                        │    in PostgreSQL            │
     │                                        ├─────────────────────────────►│
     │                                        │  Clear lockout state        │
     │                                        │                               │
     │  4. Response: { "access_token": "...", "refresh_token": "..." (cookie) }
     │◄───────────────────────────────────────┤                               │
     │                                        │                               │
```

### Access Token Creation

When a user successfully authenticates, the `TokenService.generate_tokens()` method:

1. Generates a unique `token_id` (16-byte URL-safe random)
2. Creates a JWT access token (15-minute lifetime, RS256 signed)
3. Creates a JWT refresh token (30-day lifetime)
4. Stores the refresh token hash + metadata in PostgreSQL
5. Returns access token in JSON body, refresh token in HttpOnly cookie

### Refresh Token Rotation

On every `/api/auth/refresh/` call:

1. Reads refresh token from HttpOnly cookie
2. Validates JWT signature
3. Checks token exists in database (hashed)
4. Verifies token not revoked/expired
5. **Rotates:** Marks old token as revoked, creates new token pair
6. **Replay Detection:** If token not in DB but hash exists → replay attack → invalidate all user sessions

### Logout Flow

Two logout patterns are supported:

| Endpoint | Auth Required | Behavior |
|---|---|---|
| POST /api/auth/signout/ | No (cookie-based) | Revokes current refresh token, clears cookie |
| DELETE /api/auth/sessions/{id}/ | Yes | Revokes specific session |
| DELETE /api/auth/sessions/all/ | Yes | Revokes ALL sessions (logout everywhere) |

### Device Tracking

Device identification uses a combination of:
- User-Agent header
- Accept-Language header
- Client IP address

These are combined and SHA-256 hashed to produce a 32-character `device_id`. This ID is:
- Embedded in both access and refresh tokens
- Stored in the RefreshToken table
- Used to identify sessions in the `/sessions/` endpoint
- Used to highlight the current device in session lists

---

## 5. JWT Architecture

### Access Token Structure

The access token is a **stateless JWT** signed with RS256 (asymmetric). It contains:

```json
{
  "sub": "745918c2-e8ac-47fa-90aa-4cb7e1bce125",
  "email": "user@example.com",
  "name": "John Doe",
  "workspace_ids": ["ws-uuid-1", "ws-uuid-2"],
  "roles": {
    "ws-uuid-1": "owner",
    "ws-uuid-2": "member"
  },
  "device_id": "a1b2c3d4e5f6...",
  "token_type": "access",
  "iat": 1779252729,
  "exp": 1779253529,
  "jti": "token-uuid"
}
```

| Claim | Description |
|---|---|
| `sub` | User UUID (subject) |
| `email` | User email |
| `name` | User display name |
| `workspace_ids` | List of workspace UUIDs user belongs to |
| `roles` | Role per workspace (owner/admin/member/viewer) |
| `device_id` | Device identifier from request |
| `token_type` | Always "access" |
| `iat` | Issued at (Unix timestamp) |
| `exp` | Expiration (Unix timestamp, default 15 minutes) |
| `jti` | JWT ID (unique per token) |

### Refresh Token Structure

The refresh token is also a JWT but with different claims:

```json
{
  "sub": "745918c2-e8ac-47fa-90aa-4cb7e1bce125",
  "email": "user@example.com",
  "name": "John Doe",
  "device_id": "a1b2c3d4e5f6...",
  "token_id": "abc123def456...",
  "token_type": "refresh",
  "iat": 1779252729,
  "exp": 1797852729,
  "jti": "refresh-uuid"
}
```

| Claim | Description |
|---|---|
| `token_id` | Unique ID stored in database for rotation tracking |
| `token_type` | Always "refresh" |
| `exp` | Expiration (default 30 days) |

### RS256 vs HS256 Explanation

**RS256 (RSA Signature with SHA-256):**
- Uses asymmetric key pair: private key signs, public key verifies
- Private key stays on Identity Service; public key is shared
- Other services can verify tokens without calling Identity Service
- Used by GitHub, Google, Stripe — industry standard

**HS256 (HMAC with SHA-256):**
- Uses shared secret: same key signs and verifies
- Requires every service to have the same secret
- If one service is compromised, all are compromised
- Simpler but less secure — **not used in this implementation**

### Token Expiration Strategy

| Token Type | Lifetime | Rationale |
|---|---|---|
| Access Token | 15 minutes | Short lifetime limits exposure if token is leaked |
| Refresh Token | 30 days | Long lifetime enables persistent sessions; rotation keeps it secure |
| JWT Signing Key | Rotated via JWKS | Key rotation schedule (future improvement) |

### Token Verification Flow

```
┌─────────┐                           ┌──────────────────┐
│ Service │                           │ Identity Service │
└────┬────┘                           └────────┬─────────┘
     │                                        │
     │  1. Request with Authorization: Bearer <jwt>   │
     ├────────────────────────────────────────►│
     │                                        │
     │  2. Get JWKS (cached, 1 hour TTL)                 │
     │     GET /.well-known/jwks.json                  │
     │◄────────────────────────────────────────┤
     │  (or use cached from startup)                    │
     │                                        │
     │  3. Verify signature using RS256               │
     │     - Decode JWT header → get "kid"             │
     │     - Find matching key in JWKS                  │
     │     - Verify signature                          │
     │                                        │
     │  4. Validate claims:                            │
     │     - exp: not expired                          │
     │     - iat: not issued in future                │
     │     - token_type: "access"                     │
     │                                        │
     │  5. Extract user info from claims               │
     │     → request.user = user                     │
     │                                        │
```

### JWT Middleware/Auth Backend Explanation

DRF uses **authentication classes** that implement the `authenticate()` method. Two are registered:

1. **APIKeyAuthentication** (`api_keys.authentication.backend.APIKeyAuthentication`)
   - Checks if Authorization header starts with `Bearer krv_live_`
   - If yes, verifies API key; otherwise returns `None` (pass through)
   
2. **JWTAuthentication** (`rest_framework_simplejwt.authentication.JWTAuthentication`)
   - Standard SimpleJWT authentication
   - Parses Bearer token, verifies signature, extracts user

The order matters: API keys are checked first, then JWTs. This allows API keys to coexist with JWT authentication in the same service.

---

## 6. Redis Architecture

### EXACTLY How Redis Is Used

Redis is a critical component of the Identity Service, handling five distinct use cases:

| Use Case | Key Pattern | TTL | Description |
|---|---|---|---|
| Login Lockout | `login_lockout:{email}:{ip}` | 15 min | Account lockout after 5 failures |
| Login Attempts | `login_attempts:{email}:{ip}` | 15 min | Failure counter per email+IP |
| OTP Storage | `otp:{email}` | 5 min | One-time password cache |
| JWT Blacklist | `jwt_blacklist:{jti}` | 15 min | Revoked access tokens |
| Session Cache | `session:{user_id}:{device_id}` | 30 min | Cached session metadata |

### Session Storage

While the primary session data lives in PostgreSQL (RefreshToken table), Redis is used for:

- **Revocation Check:** When validating a refresh token, Redis is checked first for a blacklist entry.
- **Session Metadata:** Caches recent session metadata for fast lookup in `/sessions/`.

### Refresh Token Storage

Refresh tokens are **NOT** stored in Redis — they are stored in PostgreSQL for durability. Redis is only used for lockout, OTP, and blacklist management.

### Rate Limiting

The `LoginLockoutManager` in `security.py` implements rate limiting:

```python
# Record failure
redis.incr(f"login_attempts:{email}:{ip}")
redis.expire(f"login_attempts:{email}:{ip}", 900)  # 15 min

# After 5 failures
redis.setex(f"login_lockout:{email}:{ip}", 900, 1)  # Lock for 15 min
redis.delete(f"login_attempts:{email}:{ip}")  # Reset counter
```

### Blacklist/Revocation Handling

When a user logs out or a session is revoked:
1. The refresh token record in PostgreSQL is marked `revoked=True`
2. The access token's `jti` (JWT ID) is added to Redis blacklist
3. Subsequent requests with that access token are rejected

### Cache Strategy

Redis caching follows a **cache-aside pattern**:

1. **Read:** Check Redis → if miss, read PostgreSQL → write Redis → return
2. **Write:** Write to PostgreSQL → invalidate Redis cache
3. **TTL:** All caches have sensible TTLs (no permanent caching)

### Redis Key Naming Strategy

All keys follow a consistent pattern: `{service}:{resource}:{identifier}:{variant}`

Examples:
- `login_lockout:test@example.com:192.168.1.1`
- `otp:user@example.com`
- `jwt_blacklist:abc123-def456`

### TTL Strategy

| Key Type | TTL | Rationale |
|---|---|---|
| Login lockout | 15 minutes | Enough to deter attacks, not punish users |
| Login attempts | 15 minutes | Aligns with lockout duration |
| OTP | 5 minutes | Single-use, short-lived |
| JWT blacklist | 15 minutes | Aligned with access token lifetime |
| Session cache | 30 minutes | Half of refresh token lifetime |

### Why Redis Is Important for Auth Scalability

1. **Speed:** Redis operations are sub-millisecond, orders of magnitude faster than PostgreSQL.
2. **Atomic Operations:** INCR, SETNX, EXPIRE are atomic — perfect for rate limiting.
3. **Distributed State:** All auth service instances share the same lockout state.
4. **Persistence:** Optional persistence (RDB/AOF) ensures state survives restarts.
5. **Memory-Based:** All auth-related state fits in memory — no disk I/O.

---

## 7. API Key Authentication

### How API Keys Are Generated

API keys are generated using cryptographically secure random bytes:

```python
# From generator.py
random_part = secrets.token_hex(32)  # 32 bytes = 64 hex chars
raw_key = f"krv_live_{random_part}"  # Total: 72 chars
prefix = f"krv_live_{random_part[:8]}"  # Display prefix: 16 chars
```

### Prefix System

The prefix `krv_live_` serves multiple purposes:

1. **Identification:** Instantly recognizable as a Kraivor key
2. **Secret Scanning:** GitGuardian, GitLeaks, truffleHog can be configured to flag this pattern
3. **Format Validation:** O(1) check — if it doesn't start with `krv_live_`, it's not a Kraivor API key
4. **Environment Differentiation:** Future `krv_test_` prefix for development keys

**Example:**
```
Full key:   krv_live_3f8b2a9c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a
Prefix:    krv_live_3f8b2a9c
```

### SHA-256 Hashing

**Crucial Security Decision:** The raw key is NEVER stored. Only its SHA-256 hash is stored in the database.

```python
# From hasher.py
def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
```

Why SHA-256 and not Argon2/bcrypt?
- API keys have **maximum entropy** (32 bytes of random data)
- Argon2/bcrypt add 200-500ms latency per request — unnecessary for high-entropy inputs
- SHA-256 is the industry standard (used by GitHub, Stripe, OpenAI)

### Why Raw Keys Are Never Stored

1. **Attack Surface Reduction:** If the database is compromised, only hashes are exposed — attackers cannot use them directly.
2. **Display-once Pattern:** User sees raw key once at creation; if they lose it, they must regenerate.
3. **Audit Trail:** Only the hash is stored, so even admins cannot use API keys.

### Scoped Permissions

API keys support granular permissions via scopes:

```python
VALID_SCOPES = frozenset({
    "analysis:read",    # Read analysis results
    "analysis:write",   # Trigger new analyses  
    "ai:chat",          # Use AI chat interface
    "admin"             # Full access (org admins only)
})
```

Scopes are stored as a JSON array in the database and checked at the permission layer.

### Revocation Flow

```python
# From key_service.py
def revoke_api_key(key_id: str, user) -> bool:
    key = APIKey.objects.get(id=key_id, user=user)
    key.revoked = True
    key.save()
    # Optionally: revoke associated refresh tokens
    return True
```

### Expiration Flow

API keys can have optional expiration:

```python
expires_at = models.DateTimeField(null=True, blank=True)

def is_valid(self) -> bool:
    return not (
        self.revoked
        or (self.expires_at and self.expires_at < timezone.now())
    )
```

### Organization API Keys

(Future enhancement — not yet implemented)

The current implementation ties API keys directly to users. Future version will support organization-level API keys with organization-level scoping.

### CI/CD Integration Use Cases

API keys are designed for programmatic access:

```bash
# Example: Trigger an analysis from CI/CD
curl -X POST https://api.kraivor.com/api/analysis/ \
  -H "Authorization: Bearer krv_live_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/org/repo"}'
```

Use cases:
- **CI/CD Pipelines:** Trigger analyses on every push
- **Monitoring:** Fetch health metrics via API
- **Automation:** Trigger batch jobs without user credentials
- **Service Accounts:** Long-lived access for background services

---

## 8. DRF Authentication Backend

### How DRF Authentication Classes Work

Django REST Framework's authentication system works as follows:

1. **Request arrives** → DRF runs through `DEFAULT_AUTHENTICATION_CLASSES` in order
2. **Each class** calls `authenticate(request)` → returns `(user, auth)` tuple or `None`
3. **First non-None result** is used; subsequent classes are skipped
4. **If all return None** → request.user is `AnonymousUser`

### Request Lifecycle

```
HTTP Request
    │
    ▼
Django Middleware (CORS, Auth, etc.)
    │
    ▼
DRF View.dispatch()
    │
    ▼
DRF Initial: run auth & permission
    │
    ├─► APIKeyAuthentication.authenticate()
    │       - Check "Bearer krv_live_..." format
    │       - Hash key, lookup in DB
    │       - Verify not revoked/expired
    │       - Return (User, APIKey)
    │
    ├─► JWTAuthentication.authenticate()
    │       - Parse "Bearer <jwt>"
    │       - Verify signature
    │       - Return (User, Token)
    │
    ├─► (if both return None) → AnonymousUser
    │
    ▼
Permission Classes (IsAuthenticated, etc.)
    │
    ▼
View handler (post/put/patch/get/delete)
    │
    ▼
Response
```

### Header Parsing

The authentication backend parses the `Authorization` header:

```python
# From authentication/backend.py
auth_header = request.META.get("HTTP_AUTHORIZATION", "")
parts = auth_header.split()

if len(parts) != 2 or parts[0].lower() != "bearer":
    return None  # Not a bearer token

raw_token = parts[1]
```

### User Resolution

Once authenticated, the user is resolved:

- **JWT:** Extract `user_id` from token claims → lookup in PostgreSQL
- **API Key:** Extract `user` from APIKey model relationship

Both return a Django `User` instance attached to `request.user`.

### Permission Validation

After authentication, permission classes are checked:

```python
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}
```

Custom permissions can check:
- Workspace membership
- Role (owner/admin/member/viewer)
- API key scopes

---

## 9. Multi-Tenant Security

### Organization Isolation

The Identity Service implements multi-tenancy through **workspaces** (future: organizations). While the current implementation focuses on user identity, the architecture supports organization-level isolation:

1. **User → Workspaces:** Users can belong to multiple workspaces
2. **JWT Claims:** Token includes `workspace_ids` and `roles`
3. **Service Validation:** Downstream services validate workspace access via JWT claims

### Scoped Access

Each request carries workspace context in the JWT:

```json
{
  "workspace_ids": ["ws-uuid-1", "ws-uuid-2"],
  "roles": {
    "ws-uuid-1": "owner",
    "ws-uuid-2": "member"
  }
}
```

Services use these claims to:
- Filter queries to the user's workspace
- Enforce role-based permissions
- Log audit events with workspace context

### Role-Based Access

| Role | Permissions |
|---|---|
| Owner | Full workspace access, delete workspace, manage billing |
| Admin | Manage members, manage repositories, all content |
| Member | Create content, trigger analyses |
| Viewer | Read-only access to results and reports |

### Row-Level Security Concepts

(Implementation in downstream services)

PostgreSQL Row-Level Security (RLS) can be enabled on tables:

```sql
CREATE POLICY workspace_isolation ON analysis_jobs
  USING (workspace_id IN (
    SELECT workspace_id 
    FROM workspace_members 
    WHERE user_id = current_user_id
  ));
```

This ensures that even SQL-level access respects workspace boundaries.

### Tenant-Safe Architecture

The Identity Service is tenant-safe by design:

- **No Tenant ID in User Model:** Users are independent entities; workspace membership is a separate relationship
- **Tenant Isolation in Queries:** All queries to user data must go through service layer, which enforces tenant filtering
- **Audit Logging:** All events include workspace context when applicable

---

## 10. OAuth Architecture

### GitHub OAuth

The GitHub OAuth flow:

```
User                        Identity Service              GitHub
  │                              │                           │
  │  1. GET /api/auth/oauth/github/                         │
  │◄─────────────────────────────│                           │
  │      Redirect to GitHub OAuth URL                      │
  │◄─────────────────────────────│                           │
  │                              │  2. User authorizes       │
  │─────────────────────────────►│────────────────────────►│
  │                              │                           │
  │                              │  3. Callback with code   │
  │◄─────────────────────────────│◄────────────────────────│
  │                              │                           │
  │                              │  4. Exchange code for   │
  │                              │     access_token         │
  │                              │◄────────────────────────►│
  │                              │                           │
  │                              │  5. Get user info        │
  │                              │     (email, name)       │
  │                              │◄────────────────────────►│
  │                              │                           │
  │  6. Create/Link user        │                           │
  │  7. Issue JWT tokens       │                           │
  │◄─────────────────────────────│                           │
```

Implementation: `authentication/oauth/views.py`, `authentication/oauth/github.py`

### Google OAuth

Similar to GitHub but with additional email verification handling:

```python
# From google/services/identity.py
if user_info.email_verified:
    user.email_verified = True  # Trust Google's verification
```

Implementation: `authentication/oauth/google/`

### Apple OAuth

(Architecture defined, implementation pending)

Apple OAuth adds complexity:
- **Sign in with Apple JS** requires client-side validation
- Email may be "private relay" — must handle `notvisible@icloud.com`

### OAuth Callback Flow

The OAuth callback handles:

1. **State Validation:** Verify the `state` parameter to prevent CSRF
2. **Code Exchange:** Swap authorization code for access token
3. **User Info:** Fetch user profile (email, name)
4. **Identity Lookup:** Check if OAuthIdentity exists for this provider+provider_user_id
5. **User Resolution:**
   - If identity exists → return associated user
   - If email matches existing user → link identity
   - If new user → create new user with identity
6. **Token Issuance:** Generate JWT pair for the resolved user

### Token Exchange

OAuth access tokens are stored encrypted:

```python
# From models.py
access_token_encrypted = models.TextField(null=True, blank=True)
refresh_token_encrypted = models.TextField(null=True, blank=True)
```

Encryption uses `OAUTH_TOKEN_ENCRYPTION_KEY` (AES-256-GCM).

### Identity Linking

Users can link multiple OAuth identities:

```python
class OAuthIdentity(models.Model):
    user = models.ForeignKey("users.User", ...)
    provider = models.CharField(...)  # github, google, apple
    provider_user_id = models.CharField(...)
    provider_email = models.EmailField(...)
```

A user can have multiple identities, enabling:
- Account recovery via alternate provider
- Migration between providers

---

## 11. Security Architecture

### Password Hashing

User passwords are hashed using Django's default hasher (currently PBKDF2, with Argon2 planned):

```python
# From security.py
def check_password(plain_password: str, hashed_password: str) -> bool:
    return django_check_password(plain_password, hashed_password)
```

Django's `make_password()` uses:
- **PBKDF2** (default) — 720,000 iterations (configurable)
- **Argon2** (recommended for migration) — memory-hard, resistant to GPU cracking

### Argon2/Bcrypt Explanation

| Hasher | Best For | Strengths | Weaknesses |
|---|---|---|---|
| PBKDF2 | Default Django | Well-studied, NIST approved | CPU-bound, vulnerable to GPU |
| Argon2id | Recommended | Memory-hard, GPU-resistant | Newer, less battle-tested |
| Bcrypt | Legacy | Widely used | Capable of only 72-char passwords |

For this service:
- **User passwords:** PBKDF2 (Django default), with path to Argon2
- **API keys:** SHA-256 (high entropy, no need for slow hashing)
- **Token hashes:** SHA-256 (same reasoning)

### CSRF Protection

The service uses Django's CSRF middleware with additional measures:

1. **Cookie-based Auth:** Refresh tokens in HttpOnly cookies — JS cannot read them
2. **SameSite Attribute:** `SameSite=Lax` prevents cross-site request forgery
3. **API-only Mode:** No Django templates → reduced CSRF surface

### Rate Limiting

Rate limiting is implemented at two levels:

1. **Login Lockout:** After 5 failures per email+IP → 15-minute lockout
2. **API Rate Limiting:** Kong or Nginx layer → 300 req/min authenticated

### Replay Attack Prevention

The refresh token rotation system detects replay attacks:

```python
# From tokens.py
stored_token = RefreshToken.objects.get(token_hash=token_hash, user=user, revoked=False)
# If token not in DB but hash exists → replay attack
if token_exists:
    self._revoke_all_user_tokens(user)  # Invalidate ALL sessions
    raise TokenReusedError("Replay attack detected")
```

### Device Fingerprinting

Device ID is generated from:
- User-Agent
- Accept-Language
- Client IP

```python
# From security.py
def generate_device_id(request) -> str:
    raw = f"{user_agent}:{accept_language}:{ip}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
```

### Audit Logging

All authentication events are logged:

```python
# From views.py
log_auth_event(
    event_type="login_success",
    user_id=str(user.id),
    email=email,
    ip=ip,
    device_id=device_id,
    success=True,
    method="password",
)
```

### Secrets Management

Secrets are managed through:
- **Development:** `.env` files (never committed)
- **Production:** Kubernetes secrets / AWS Secrets Manager
- **CI/CD:** GitHub Actions secrets

Key secrets:
- `JWT_PRIVATE_KEY_PATH` — RSA private key for signing
- `JWT_PUBLIC_KEY_PATH` — RSA public key for verification
- `OAUTH_TOKEN_ENCRYPTION_KEY` — AES key for OAuth token encryption
- `EMAIL_HOST_PASSWORD` — SMTP credentials

### OWASP Considerations

| OWASP Risk | Mitigation |
|---|---|
| A01: Broken Access Control | Role-based permissions, workspace isolation |
| A02: Cryptographic Failures | RS256, SHA-256, PBKDF2, encrypted OAuth tokens |
| A03: Injection | ORM, parameterized queries, no raw SQL |
| A04: Insecure Design | Multi-step auth, rate limiting, session revocation |
| A05: Security Misconfiguration | Hardened headers, minimal CORS, secure cookies |
| A06: Vulnerable Components | Regular dependency scanning, Dependabot |
| A07: Auth Failures | Lockout, rotation, replay detection, audit logs |

---

## 12. Database Architecture

### Core Tables

```sql
-- Users (auth_users)
CREATE TABLE auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(128),  -- PBKDF2 hash
    name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Refresh Tokens (auth_refresh_tokens)
CREATE TABLE auth_refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id),
    token_hash VARCHAR(255) NOT NULL,
    device_id VARCHAR(255),
    device_name VARCHAR(255),
    device_type VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

-- API Keys (identity_api_keys)
CREATE TABLE identity_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    prefix VARCHAR(20) NOT NULL,
    scopes JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    revoked BOOLEAN DEFAULT FALSE
);

-- OAuth Identities (auth_oauth_identities)
CREATE TABLE auth_oauth_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id),
    provider VARCHAR(50) NOT NULL,  -- github, google, apple
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255),
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    expires_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ,
    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Relationships

```
User (1) ────< RefreshToken
User (1) ────< APIKey
User (1) ────< OAuthIdentity
```

### UUID Usage

All primary keys use UUIDs (`gen_random_uuid()`):

- **Why UUIDs?**
  - No database sequence → works across distributed databases
  - Non-guessable → reduces enumeration attacks
  - Merge-friendly → can merge data from different sources

### API Key Schema

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID FK | Owner |
| name | VARCHAR(255) | Display name |
| key_hash | VARCHAR(255) | SHA-256 hash |
| prefix | VARCHAR(20) | Display prefix |
| scopes | JSONB | Permission array |
| expires_at | TIMESTAMPTZ | Optional expiration |
| revoked | BOOLEAN | Soft delete |

### Session Schema

| Field | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID FK | Owner |
| token_hash | VARCHAR(255) | SHA-256 of refresh token |
| device_id | VARCHAR(255) | Device fingerprint |
| ip_address | INET | Client IP |
| user_agent | TEXT | HTTP User-Agent |
| expires_at | TIMESTAMPTZ | Expiration |
| revoked | BOOLEAN | Revocation flag |
| last_used_at | TIMESTAMPTZ | Last use time |

### Organization Membership Schema

(Future enhancement)

```sql
-- Planned schema
CREATE TABLE identity_organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE identity_organization_members (
    organization_id UUID REFERENCES identity_organizations(id),
    user_id UUID REFERENCES auth_users(id),
    role VARCHAR(50) NOT NULL,  -- owner, admin, member
    PRIMARY KEY (organization_id, user_id)
);
```

---

## 13. Celery & Background Jobs

### Email Verification Jobs

When a user registers, the view calls `email_service.send_verification_email()`:

```python
# From email_service.py
def send_verification_email(self, user: User, token: str) -> None:
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    verify_url = f"{frontend_url}/verify-email?token={token}"
    # Send via SMTP (MailHog in dev, SES in prod)
```

Currently synchronous; future: Celery task for queueing.

### Cleanup Jobs

Planned Celery tasks:

| Task | Schedule | Description |
|---|---|---|
| `cleanup_expired_tokens` | Daily | Remove expired refresh tokens |
| `cleanup_expired_api_keys` | Daily | Revoke expired API keys |
| `cleanup_unverified_users` | Weekly | Remove users never verified after 7 days |
| `rotate_jwt_signing_keys` | Monthly | Rotate RS256 key pair |

### Token Cleanup

```python
# Planned Celery task
@app.task
def cleanup_expired_tokens():
    count = RefreshToken.objects.filter(
        expires_at__lt=timezone.now(),
        revoked=False
    ).update(revoked=True)
    logger.info(f"Cleaned up {count} expired tokens")
```

### Async Notification Flow

(Future enhancement)

When analysis completes, notification service consumes Kafka event and sends email. The Identity Service will publish events rather than sending directly.

---

## 14. Docker & Kubernetes Integration

### How Auth Service Runs in Containers

```yaml
# docker-compose.yml (conceptual)
services:
  auth:
    build: ./services/auth
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgres://...
      - REDIS_URL=redis://...
      - JWT_PRIVATE_KEY_PATH=/keys/jwt-private.pem
      - JWT_PUBLIC_KEY_PATH=/keys/jwt-public.pem
    volumes:
      - ./services/auth/.keys:/keys:ro
    depends_on:
      - postgres
      - redis
```

### Scaling Strategy

Horizontal scaling with Kubernetes:

```yaml
# deployment.yaml (conceptual)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: identity-service
spec:
  replicas: 3  # Start with 3, auto-scale based on CPU/memory
  selector:
    matchLabels:
      app: identity-service
  template:
    spec:
      containers:
        - name: auth
          image: kraivor/identity-service:latest
          ports:
            - containerPort: 8001
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

### Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /api/health/
    port: 8001
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /api/health/
    port: 8001
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Horizontal Scaling

- **Stateless API:** No session state in application → any pod can handle any request
- **Database Connection Pool:** PgBouncer handles connection multiplexing
- **Redis Connection Pool:** Jedis/Lettuce pool shared across requests
- **Auto-scaling:** KEDA scales based on request queue depth (Celery)

### Stateless API Explanation

A **stateless API** does not store per-user session data in memory. Every request must contain all necessary information (JWT) or retrieve state from a database/Redis. This enables:

- **Horizontal Scaling:** Add/remove pods without session affinity
- **Rolling Updates:** Kill pods without user impact
- **Failure Isolation:** One pod failure doesn't affect others

---

## 15. CI/CD Integration

### GitHub Actions Auth Flow

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          cd services/auth
          python -m pytest --junitxml=report.xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### API Key Usage in CI

CI/CD pipelines use API keys for programmatic access:

```yaml
# Example: Run analysis after deployment
deploy:
  steps:
    - name: Trigger analysis
      run: |
        curl -X POST $API_URL/analysis/ \
          -H "Authorization: Bearer ${{ secrets.API_KEY }}" \
          -d '{"repo_url": "..."}'
```

### Secrets Handling

| Secret | Storage | Usage |
|---|---|---|
| API Key | GitHub Secrets | CI/CD pipelines |
| JWT Keys | Kubernetes Secrets | Service pods |
| Database URL | Kubernetes Secrets / AWS Secrets Manager | Service configuration |
| SMTP Credentials | Kubernetes Secrets | Email sending |

### Deployment Validation

Pre-deployment checks:
1. **Lint:** `ruff check`, `black --check`
2. **Type Check:** `mypy`
3. **Tests:** `pytest` with >80% coverage
4. **Security Scan:** `bandit`, `safety`
5. **Container Scan:** Trivy for CVE scanning

---

## 16. Monitoring & Observability

### Logging

Structured JSON logging with correlation IDs:

```python
# Every log includes:
{
    "timestamp": "2026-05-20T10:30:00Z",
    "level": "INFO",
    "service": "identity-service",
    "event": "login_success",
    "user_id": "745918c2-...",
    "ip": "192.168.1.1",
    "method": "password",
    "correlation_id": "abc123"
}
```

### Metrics

Prometheus metrics exposed at `/metrics`:

| Metric | Type | Description |
|---|---|---|
| `auth_login_total` | Counter | Total login attempts |
| `auth_login_success_total` | Counter | Successful logins |
| `auth_token_refresh_total` | Counter | Token refresh operations |
| `auth_rate_limit_exceeded_total` | Counter | Rate limit hits |
| `auth_sessions_active` | Gauge | Active sessions |

### Authentication Monitoring

Key dashboards:
- Login success/failure rate
- Token refresh rate
- API key usage
- Failed authentication by IP
- Account lockout frequency

### Suspicious Activity Tracking

Alerts configured for:
- High failed login rate (potential brute force)
- Token replay detected (security incident)
- Multiple concurrent sessions from different IPs (account sharing)
- API key usage from new IP (potential key compromise)

### Prometheus/Grafana Ideas

- **Login Dashboard:** Success rate, method breakdown, geo distribution
- **Token Dashboard:** Refresh rate, rotation latency, revocation rate
- **Security Dashboard:** Lockouts, rate limits, suspicious patterns

---

## 17. Sequence Diagrams

### Login Flow

```mermaid
sequenceDiagram
    participant Client
    participant Identity
    participant Redis
    participant PostgreSQL

    Note over Client, Identity: Step 1: Identify
    Client->>Identity: POST /api/auth/signin/identify/<br/>{email: "user@example.com"}
    Identity->>Redis: Check lockout (login_lockout:email:ip)
    Redis-->>Identity: not locked
    Identity->>PostgreSQL: SELECT user WHERE email=?
    PostgreSQL-->>Identity: user exists, email_verified=true
    Identity-->>Client: {next_step: "choose_method", methods: ["password", "otp"]}

    Note over Client, Identity: Step 2: Password Verify
    Client->>Identity: POST /api/auth/signin/password/<br/>{email, password}
    Identity->>PostgreSQL: SELECT password_hash
    Identity->>Identity: verify_password(password, hash)
    alt Invalid password
        Identity->>Redis: INCR login_attempts:email:ip
        Identity->>Redis: SET login_lockout:email:ip (if >=5 failures)
        Identity-->>Client: 401 Invalid credentials
    else Valid password
        Identity->>Redis: DEL login_attempts:email:ip
        Identity->>Identity: generate JWT pair
        Identity->>PostgreSQL: INSERT refresh_token (hashed)
        Identity-->>Client: {access_token, refresh_token (cookie)}
    end
```

### Refresh Flow

```mermaid
sequenceDiagram
    participant Client
    participant Identity
    participant PostgreSQL
    participant Redis

    Client->>Identity: POST /api/auth/refresh/<br/>Cookie: refresh_token
    Identity->>Identity: Parse JWT, extract token_id
    Identity->>PostgreSQL: SELECT refresh_token WHERE hash=?
    alt Token not found or revoked
        Identity-->>Client: 401 Invalid token
    else Token found
        Identity->>PostgreSQL: UPDATE refresh_token SET revoked=true
        Identity->>Identity: Generate new token pair
        Identity->>PostgreSQL: INSERT new refresh_token
        Identity-->>Client: {new_access_token, new_refresh_token (cookie)}
    end
```

### API Key Auth Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Identity
    participant PostgreSQL

    Client->>API: GET /api/analysis/<br/>Authorization: Bearer krv_live_abc123...
    API->>Identity: Forward request (internal)
    Identity->>Identity: is_api_key_format(token)?
    alt Not Kraivor format
        Identity->>Identity: Return None (let JWT backend try)
    else Is Kraivor format
        Identity->>PostgreSQL: SELECT api_key WHERE hash=sha256(token)
        alt Not found or expired/revoked
            Identity-->>API: 401 Invalid API key
        else Found and valid
            Identity->>PostgreSQL: UPDATE last_used_at
            Identity-->>API: 200 OK (user, api_key)
        end
    end
    API-->>Client: Response
```

### OAuth Login Flow

```mermaid
sequenceDiagram
    participant User
    participant Client
    participant Identity
    participant GitHub

    User->>Client: Click "Sign in with GitHub"
    Client->>Identity: GET /api/auth/oauth/github/
    Identity->>Identity: Generate state token
    Identity-->>Client: 302 Redirect to GitHub

    Client->>GitHub: Authorization request<br/>client_id=..., redirect_uri=..., state=...
    User->>GitHub: Authorize
    GitHub-->>Client: 302 Redirect to callback<br/>?code=...&state=...

    Client->>Identity: GET /api/auth/oauth/github/callback/<br/>?code=...&state=...
    Identity->>GitHub: POST https://github.com/login/oauth/access_token<br/>code=..., client_id=..., client_secret=...
    GitHub-->>Identity: {access_token: "..."}
    Identity->>GitHub: GET https://api.github.com/user<br/>Authorization: Bearer ...
    GitHub-->>Identity: {login: "user", email: "user@example.com"}
    
    alt Existing OAuth identity
        Identity->>PostgreSQL: SELECT user FROM oauth_identities
    else New user
        Identity->>PostgreSQL: INSERT user, INSERT oauth_identity
    end
    
    Identity->>Identity: Generate JWT pair
    Identity-->>Client: {access_token, refresh_token}
```

### Logout Flow

```mermaid
sequenceDiagram
    participant Client
    participant Identity
    participant PostgreSQL

    Client->>Identity: POST /api/auth/signout/<br/>Cookie: refresh_token
    Identity->>Identity: Parse JWT to get token_id
    Identity->>PostgreSQL: UPDATE refresh_token SET revoked=true<br/>WHERE token_hash=hash(token)
    Identity->>Identity: Create clear-cookie response
    Identity-->>Client: 200 OK (clears refresh_token cookie)
```

### Revocation Flow

```mermaid
sequenceDiagram
    participant Client
    participant Identity
    participant PostgreSQL
    participant Redis

    alt Single Session
        Client->>Identity: DELETE /api/auth/sessions/{session_id}/<br/>Authorization: Bearer ...
        Identity->>PostgreSQL: UPDATE refresh_token SET revoked=true<br/>WHERE id=session_id AND user=request.user
        Identity-->>Client: 200 OK
        
    else All Sessions
        Client->>Identity: DELETE /api/auth/sessions/all/<br/>Authorization: Bearer ...
        Identity->>PostgreSQL: UPDATE refresh_token SET revoked=true<br/>WHERE user=request.user AND revoked=false
        PostgreSQL-->>Identity: 3 (revoked count)
        
        Note over Identity, Redis: Optional: blacklist all access tokens
        Identity->>Redis: SET jwt_blacklist:{jti} 1 (for each jti)
        Identity-->>Client: 200 OK {revoked_count: 3}
    end
```

---

## 18. Redis Data Flow

### Login Lockout Data Flow

```mermaid
flowchart TD
    A[Login Request] --> B{User/Pass Valid?}
    B -->|No| C[Increment Counter]
    C --> D{Counter >= 5?}
    D -->|Yes| E[Set Lockout Key<br/>TTL: 15 min]
    D -->|No| F[Return 401]
    E --> F
    B -->|Yes| G[Clear Counter & Lockout]
    F --> H[Return Error]
    G --> I[Generate Tokens]
    I --> J[Return Tokens]
    
    style E fill:#f96
    style G fill:#9f6
```

### OTP Flow

```mermaid
sequenceDiagram
    participant User
    participant Identity
    participant Redis

    User->>Identity: POST /api/auth/signin/otp/send/
    Identity->>Redis: SET otp:user@example.com "123456"<br/>EX 300 (5 min)
    Redis-->>Identity: OK
    Identity->>Identity: Send email with OTP
    Identity-->>User: 200 OK
    
    User->>Identity: POST /api/auth/signin/otp/verify/<br/>{otp_code: "123456"}
    Identity->>Redis: GET otp:user@example.com
    alt OTP matches
        Redis-->>Identity: "123456"
        Identity->>Redis: DEL otp:user@example.com
        Identity->>Identity: Generate tokens
        Identity-->>User: {access_token, refresh_token}
    else OTP mismatch/expired
        Redis-->>Identity: nil
        Identity-->>User: 401 Invalid OTP
    end
```

### Redis Key Examples

```
# Login lockout
login_lockout:test@example.com:192.168.1.1
TTL: 900 seconds
Value: "1"

# Login attempts counter
login_attempts:test@example.com:192.168.1.1
TTL: 900 seconds
Value: "3"

# OTP storage
otp:user@example.com
TTL: 300 seconds
Value: "847293"

# JWT blacklist (for revoked access tokens)
jwt_blacklist:abc123-def456-ghi789
TTL: 900 seconds
Value: "1"
```

---

## 19. Full Request Lifecycle

### Authenticated Request Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLIENT                                                                        │
│                                                                             │
│ 1. User has valid access_token (JWT)                                        │
│ 2. Client makes request: GET /api/workspaces/                              │
│    Headers: Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...   │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ API GATEWAY (Kong/Nginx)                                                    │
│                                                                             │
│ 3. Rate limit check (300 req/min for auth'd)                               │
│ 4. Extract JWT from Authorization header                                    │
│ 5. Verify JWT signature using cached JWKS                                   │
│ 6. Validate claims (exp, iat, token_type)                                  │
│ 7. Add headers: X-User-ID, X-Workspace-ID, X-Correlation-ID                │
│ 8. Forward to Identity Service (internal)                                  │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ IDENTITY SERVICE                                                            │
│                                                                             │
│ 9.  Receive request                                                        │
│ 10. Check X-Internal-Request header (service-to-service)                  │
│ 11. DRF runs authentication classes in order:                              │
│     a. APIKeyAuthentication — checks for krv_live_...                     │
│        - If matches: verify key, return (User, APIKey)                     │
│        - If not: return None                                               │
│     b. JWTAuthentication — checks for standard JWT                        │
│        - If matches: verify signature, return (User, Token)               │
│        - If not: return None                                              │
│ 12. If authentication succeeded: request.user = User                       │
│ 13. Run permission classes: IsAuthenticated                                │
│ 14. Execute view handler                                                   │
│ 15. Response                                                               │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ RESPONSE TO CLIENT                                                          │
│                                                                             │
│ 16. Client receives: 200 OK {workspaces: [...]}                           │
│ 17. Client stores access_token in memory (not localStorage)                │
│                                                                             │
│ 18. When token expires (15 min):                                           │
│     - Client checks: has refresh_token cookie?                            │
│     - POST /api/auth/refresh/ → get new access_token                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Token Refresh Lifecycle

```
1. Access token expires (15 min)
2. Client has refresh_token in HttpOnly cookie
3. Client POST /api/auth/refresh/ (cookie sent automatically)
4. Identity Service:
   a. Read refresh_token from cookie
   b. Parse JWT, extract token_id, user_id
   c. Lookup refresh_token in PostgreSQL (by hash)
   d. Verify not revoked, not expired
   e. Mark old token revoked
   f. Generate new token pair
   g. Store new refresh_token hash in PostgreSQL
   h. Return new access_token + new refresh_token (cookie)
5. Client stores new access_token
6. Repeat on next expiration
```

---

## 20. Folder Structure Explanation

```
services/auth/
├── apps/
│   ├── users/                    # User management
│   │   ├── models.py              # User model
│   │   ├── views.py               # User views (profile, signup)
│   │   ├── serializers.py         # DRF serializers
│   │   ├── email_service.py       # Email sending
│   │   ├── rate_limiter.py        # Rate limiting (future)
│   │   └── verification.py        # Email verification logic
│   │
│   ├── authentication/           # Core auth logic
│   │   ├── views.py               # Sign in, sign out, sessions
│   │   ├── serializers.py         # Auth serializers
│   │   ├── tokens.py              # JWT token service
│   │   ├── jwt.py                 # JWT utilities (legacy)
│   │   ├── security.py            # Password, lockout, device ID
│   │   ├── otp.py                 # One-time password
│   │   ├── jwks.py                # JWKS endpoint
│   │   ├── cookie_utils.py        # Cookie helpers
│   │   └── oauth/                 # OAuth integration
│   │       ├── views.py           # OAuth initiate/callback
│   │       ├── github.py          # GitHub OAuth
│   │       ├── state_manager.py   # OAuth state CSRF protection
│   │       ├── encryption.py      # Token encryption
│   │       └── google/
│   │           ├── views.py       # Google OAuth views
│   │           ├── services/      # Google OAuth services
│   │           └── selectors/     # Google user selectors
│   │
│   ├── api_keys/                 # API key management
│   │   ├── models.py              # APIKey model
│   │   ├── views.py               # API key CRUD views
│   │   ├── serializers.py         # API key serializers
│   │   ├── authentication/
│   │   │   └── backend.py         # DRF auth backend
│   │   ├── permissions/
│   │   │   └── scopes.py          # Scope-based permissions
│   │   └── services/
│   │       ├── generator.py       # Key generation
│   │       ├── hasher.py          # Key hashing
│   │       └── key_service.py     # Key operations
│   │
│   └── common/                   # Shared utilities
│       ├── middleware/            # Custom middleware
│       ├── utils/                 # Helper functions
│       └── constants.py          # Constants
│
├── auth/                         # Django project settings
│   ├── settings/
│   │   ├── base.py               # Shared settings
│   │   ├── development.py        # Dev overrides
│   │   ├── staging.py            # Staging overrides
│   │   ├── production.py         # Production overrides
│   │   └── test.py               # Test overrides
│   ├── urls.py                   # URL routing
│   └── wsgi.py                   # WSGI entry point
│
├── tests/                        # Integration tests
│   ├── test_signin.py            # Sign in tests
│   ├── test_signup.py            # Sign up tests
│   ├── test_refresh_token.py     # Token refresh tests
│   ├── test_jwks.py              # JWKS endpoint tests
│   ├── test_github_oauth.py      # GitHub OAuth tests
│   ├── test_google_oauth.py      # Google OAuth tests
│   ├── test_email_verification.py# Email verification tests
│   └── test_signout_sessions.py  # Session management tests
│
├── .keys/                        # JWT signing keys (NOT in git)
│   ├── jwt-private.pem           # RS256 private key
│   └── jwt-public.pem            # RS256 public key
│
├── pyproject.toml                # UV package configuration
├── manage.py                    # Django management
└── conftest.py                  # Pytest configuration
```

---

## 21. Testing Strategy

### Pytest

The Identity Service uses **pytest** with Django integration:

```python
# conftest.py
import pytest
from django.test import Client

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def user(db):
    return User.objects.create_user(email="test@example.com", password="testpass123")
```

### Test Categories

| Category | Location | Description |
|---|---|---|
| Unit | `apps/*/tests/` | Individual functions/classes |
| Integration | `tests/` | End-to-end API flows |
| Auth | `tests/test_signin.py`, `test_signup.py` | Authentication flows |
| Security | `apps/api_keys/tests/test_hasher.py` | Crypto, hashing, edge cases |
| OAuth | `tests/test_github_oauth.py`, `test_google_oauth.py` | OAuth flows |

### Auth Tests

Example: Testing token refresh:

```python
# tests/test_refresh_token.py
def test_refresh_rotates_token(client, user, db):
    # Login to get tokens
    response = client.post("/api/auth/signin/password/", {
        "email": user.email,
        "password": "testpass123"
    })
    refresh_token = response.cookies["refresh_token"].value
    
    # Refresh
    response = client.post("/api/auth/refresh/")
    assert response.status_code == 200
    assert "access_token" in response.json()
    
    # Old token should be invalid
    response = client.post("/api/auth/refresh/", {
        "HTTP_COOKIE": f"refresh_token={refresh_token}"
    })
    assert response.status_code == 401
```

### Security Tests

Example: Testing API key hashing:

```python
# apps/api_keys/tests/test_hasher.py
def test_hash_is_deterministic():
    key = "krv_live_abc123..."
    assert hash_api_key(key) == hash_api_key(key)

def test_different_keys_different_hashes():
    key1 = "krv_live_aaa..."
    key2 = "krv_live_bbb..."
    assert hash_api_key(key1) != hash_api_key(key2)
```

### CI Testing

```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    cd services/auth
    pytest --cov=. --cov-report=xml --cov-report=html \
      --junitxml=test-results.xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

---

## 22. Current Improvements Implemented

### Enterprise-Level Decisions Already Made

| Decision | Implementation | Rationale |
|---|---|---|
| **RS256 Asymmetric Keys** | `jwks.py`, settings | Allows service-to-service JWT verification without API calls |
| **Token Rotation** | `tokens.py:validate_and_rotate()` | Prevents replay attacks, enables session management |
| **SHA-256 API Key Hashing** | `hasher.py` | Industry standard for high-entropy keys |
| **Constant-Time Comparison** | `hmac.compare_digest` | Prevents timing attacks |
| **HttpOnly Cookies** | `cookie_utils.py` | Prevents XSS token theft |
| **Multi-Step Sign-In** | `views.py:SignInIdentifyView` | Optimizes auth, supports password + OTP |
| **Device Tracking** | `security.py:generate_device_id` | Enables session management |
| **Redis Lockout** | `security.py:LoginLockoutManager` | Distributed rate limiting |
| **OAuth Ready** | `oauth/` directory | GitHub + Google + Apple architecture |
| **JWKS Endpoint** | `jwks.py` | Other services can verify JWTs |
| **UUID Primary Keys** | All models | Works with distributed databases |
| **Soft Delete** | `User.soft_delete()` | Preserves data for forensics |

---

## 23. Recommended Future Improvements

### MFA (Multi-Factor Authentication)

- **TOTP (Time-based One-Time Password):** Google Authenticator, Authy
- **SMS OTP:** Twilio integration
- **WebAuthn/Passkeys:** Passwordless, phishing-resistant

**Priority:** High — critical for enterprise customers

### JWKS Key Rotation

Currently: Static key pair loaded at startup
Future: Automated rotation with:
- New key pair generated monthly
- Old key kept for 24h (grace period)
- JWKS endpoint includes both keys with different `kid`

```python
# Planned: jwks.py enhancement
jwks = {
    "keys": [
        {"kid": "key-2025-01", "n": ..., "e": ..., "exp": ...},
        {"kid": "2024-12", "n": ..., "e": ..., "exp": ...}  # old key, grace period
    ]
}
```

### Rotating Signing Keys

Automated key rotation with database migration:

```python
# Planned: key rotation task
class KeyRotationService:
    def rotate_keys(self):
        new_key = generate_rsa_keypair()
        self.store_key(new_key, active=True)
        self.set_key_expiry(old_key, "+24h")  # grace period
```

### Session Analytics

Track session patterns:
- Login geo location
- Device changes
- Time-of-day patterns
- Anomaly scoring

### Anomaly Detection

Real-time detection of:
- Impossible travel (login from two distant locations in minutes)
- Credential stuffing (multiple accounts from same IP)
- Account takeover (new device + unusual behavior)

### WebAuthn/Passkeys

Passwordless authentication:
- FIDO2/WebAuthn standard
- Phishing-resistant
- Works across devices

### SSO/SAML

Enterprise integration:
- SAML 2.0 identity provider federation
- OIDC support
- Just-in-time provisioning

### Audit Dashboard

Admin UI for:
- Login history
- API key usage
- Session management
- Security alerts

### Security Events Pipeline

Centralized event collection:
- Kafka-based event stream
- Security information and event management (SIEM)
- Automated threat response

---

## 24. Summary

### Why This Architecture Is Production-Grade

1. **Defense in Depth:** Multiple security layers (JWT, API keys, rate limiting, lockout, encryption)
2. **Industry Standards:** RS256, SHA-256, PBKDF2, OAuth 2.0 — no custom crypto
3. **Scalable Design:** Stateless API, horizontal scaling, Redis for high-speed state
4. **Observable:** Structured logging, metrics, correlation IDs, audit trails
5. **Tested:** Comprehensive pytest suite, security tests, integration tests

### Scalability

- **Horizontal Scaling:** Add pods without session affinity
- **Database:** PgBouncer connection pooling, read replicas
- **Redis:** Cluster-ready, in-memory speed
- **API Design:** Stateless JWT verification, no per-request DB for access tokens

### Security Advantages

- **Zero-Knowledge:** Raw tokens never stored, only hashes
- **Token Rotation:** Every refresh invalidates previous — limits exposure
- **Replay Detection:** Reused tokens trigger account lockdown
- **Audit Logging:** Every auth event tracked for forensics
- **Secure Cookies:** HttpOnly, Secure, SameSite=Strict

### Enterprise Readiness

- **OAuth Ready:** GitHub, Google, Apple architecture in place
- **API Keys:** CI/CD, service accounts, scoped permissions
- **Multi-Tenant:** Workspace-based access control
- **JWKS:** Service-to-service authentication without API calls
- **Compliance:** Soft delete, audit logs, data retention

---

> **Document Maintainer:** Backend Platform Team  
> **Review Cycle:** Quarterly  
> **Version History:** 1.0 (2026-05-20) — Initial production documentation