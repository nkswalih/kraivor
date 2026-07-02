# Kraivor — Complete Production Documentation

> **Version**: 1.0.0
> **Stack**: Python 3.11+ / Node.js 18+ / Next.js 15 / Django 6 DRF / FastAPI / PostgreSQL 15 / Redis 7 / Kafka 3.9 / AWS
> **Architecture**: Microservices (6 services + Frontend)
> **License**: MIT

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [What Problem It Solves](#2-what-problem-it-solves)
3. [Key Features](#3-key-features)
4. [What Makes Kraivor Stand Out](#4-what-makes-kraivor-stand-out)
5. [System Architecture](#5-system-architecture)
6. [Microservices Breakdown](#6-microservices-breakdown)
7. [Database Schema & Design](#7-database-schema--design)
8. [Authentication & Authorization](#8-authentication--authorization)
9. [Analysis Pipeline & Engines](#9-analysis-pipeline--engines)
10. [AI System & LangGraph Agents](#10-ai-system--langgraph-agents)
11. [RAG Pipeline (Retrieval-Augmented Generation)](#11-rag-pipeline-retrieval-augmented-generation)
12. [Technology Stack — Tools Deep Dive](#12-technology-stack--tools-deep-dive)
13. [Comparison with Existing Developer Platforms](#13-comparison-with-existing-developer-platforms)
14. [Infrastructure & Deployment](#14-infrastructure--deployment)
15. [Production-Level User Management](#15-production-level-user-management)
16. [Scoring System](#16-scoring-system)
17. [Security Architecture](#17-security-architecture)
18. [Observability & Monitoring](#18-observability--monitoring)
19. [Summary & Conclusion](#19-summary--conclusion)

---

## 1. Project Overview

**Kraivor** is a unified **Developer Intelligence Platform** that combines three distinct products into a single authenticated workspace:

| Product | Target | Description |
|---------|--------|-------------|
| **Kraivor Solo** | Individual Developers | Personal engineering co-pilot — AI-powered code analysis, real-time feedback, and production readiness scoring |
| **Kraivor Team** | Engineering Teams | Multi-user workspace with CI/CD integration, team analytics, project management, knowledge spaces, community discussions |
| **Kraivor Enterprise** | Organizations | Self-hosted deployment, custom rule engines, SLA-backed support, SSO, compliance reporting |

At its core, Kraivor is not just another linter or static analysis tool. It is a **Production Intelligence Platform** that simulates real production load and predicts how code will behave under stress across five critical dimensions:

- **Performance** — How fast will this code run under load?
- **Security** — What vulnerabilities exist in the codebase?
- **Reliability** — Will the system handle failures gracefully?
- **Maintainability** — How easy is it to maintain and extend?
- **DevOps Readiness** — Is the code production-operable?

---

## 2. What Problem It Solves

### The Developer Productivity Gap

Modern engineering teams face a fragmented toolchain. They use:

- **GitHub/GitLab** for code hosting and reviews
- **Jira/Linear** for project management
- **SonarQube/CodeQL** for code quality
- **Sentry/Datadog** for monitoring
- **Slack** for communication
- **Notion/Confluence** for documentation
- **Various AI tools** (Copilot, ChatGPT) for coding assistance

This fragmentation creates **context-switching overhead**, **information silos**, and **delayed feedback loops**. A developer might write code that passes all linters but still fails catastrophically in production because no tool simulated real-world conditions.

### Kraivor's Solution

Kraivor bridges this gap by providing a **single, unified platform** that:

1. **Analyzes code deeply** — Not just syntax but architectural patterns, performance characteristics, security vulnerabilities, reliability anti-patterns, and DevOps readiness
2. **Simulates production load** — Predicts how code behaves at 100, 500, 5,000, and 50,000 concurrent users
3. **Provides AI-powered insights** — Multi-agent AI system that understands code context and provides actionable recommendations
4. **Unifies collaboration** — Project management, knowledge spaces, community discussions, and team chat in one workspace
5. **Integrates with existing workflows** — GitHub Apps, CI/CD pipelines, webhooks

---

## 3. Key Features

### 3.1 Repository Analyzer

| Feature | Description |
|---------|-------------|
| **Multi-Language Parsing** | 10 languages: Python, JavaScript/TypeScript, Go, C#, Java, PHP, Ruby, Rust, Kotlin, Elixir |
| **Production Readiness Score** | 0-100 scoring across 5 dimensions with tier classification (Critical/Needs Work/Good/Excellent) |
| **16-Stage Analysis Pipeline** | From cloning to report generation with AI enrichment |
| **Load Simulation** | Simulates traffic at 100, 500, 5K, 50K concurrent users |
| **Enterprise Report** | Auto-generated executive summary with architecture review, capacity analysis, and migration path |
| **AI-Powered Enrichment** | Each finding enriched with AI-generated explanations and fix suggestions |
| **Score History** | Track scores over time with TimescaleDB for trend analysis |

### 3.2 8 Analysis Engines

| Engine | What It Detects |
|--------|----------------|
| **Security Engine** | Code injection, XSS, SQL injection, hardcoded secrets, insecure dependencies, OWASP Top 10 |
| **Maintainability Engine** | Long methods, high cyclomatic complexity, deep nesting, duplicate code, magic numbers, missing docstrings, circular imports |
| **Reliability Engine** | Missing retries, circuit breakers, transaction misuse, race conditions, resource leaks, infinite loops, cache stampede, idempotency issues |
| **DevOps Engine** | Dockerfile issues, CI/CD misconfigurations, missing health checks, Terraform/Helm problems, observability gaps |
| **Dead Code Engine** | Unused imports, unused functions, orphan classes, unreachable code |
| **Error Detection Engine** | Bare except clauses, swallowed exceptions, missing timeouts, silent failures |
| **Performance Engine** | N+1 queries, sync-in-async, unbounded queries, CPU complexity, memory pressure, serialization bottlenecks |
| **Simulation Engine** | Load testing at scale, bottleneck detection, RPM estimation, error rate prediction |

### 3.3 AI System

| Feature | Description |
|---------|-------------|
| **Multi-Agent Architecture** | LangGraph orchestrator-specialist pattern with 6 specialized agents |
| **Multi-Provider LLM Routing** | Routes queries to optimal model: Gemini Flash, Claude Sonnet, GPT-4o, DeepSeek Coder |
| **RAG Pipeline** | AST-aware code chunking + pgvector embeddings + cosine similarity retrieval |
| **Code Analysis** | Code quality review, vulnerability analysis, architecture evaluation, Big-O analysis |
| **Streaming Responses** | Real-time token streaming for all supported LLM providers |
| **Custom Agent Configs** | Users can configure model, temperature, max_tokens, system prompts |

### 3.4 Developer Productivity Platform

| Feature | Description |
|---------|-------------|
| **Workspaces** | Multi-tenant workspaces with role-based access (Owner, Admin, Member, Viewer) |
| **Projects & Tasks** | Full project management with kanban-style boards, task links, priorities, estimates |
| **Knowledge Spaces** | Infinite canvas for documentation, diagrams, and knowledge management |
| **Community Discussions** | Reddit-style discussions with voting, comments, tags, and moderation |
| **Team Chat** | Real-time chat with rooms, DMs, and AI-powered assistance |
| **GitHub Integration** | OAuth login, GitHub App installation, auto-repository syncing |

### 3.5 Authentication & Security

| Feature | Description |
|---------|-------------|
| **JWT RS256** | Dual-token auth (access + refresh) with JWKS endpoint |
| **OAuth 2.0** | GitHub, Google, Apple OAuth providers |
| **API Keys** | Scoped API keys with rate limiting |
| **MFA Support** | Multi-factor authentication |
| **Soft Delete** | All entities support soft-delete audit trail |
| **Encrypted Secrets** | OAuth tokens encrypted at rest |

---

## 4. What Makes Kraivor Stand Out

### 4.1 Production Simulation, Not Just Linting

Traditional tools (SonarQube, CodeQL, ESLint) analyze code statically. Kraivor goes beyond by simulating actual production traffic. It predicts RPM, latency percentiles (p50/p95/p99), error rates, and bottleneck locations before code ever hits production.

### 4.2 Multi-Dimensional Scoring

Unlike single-score quality gates, Kraivor's **Production Readiness Score** is a composite of 5 orthogonal dimensions with a **critical-floor mechanism**: if any dimension drops below 50, the overall score is capped at that value. This prevents teams from gaming the system by focusing on only one aspect.

### 4.3 AI-Native Architecture

Kraivor isn't an existing tool with AI bolted on. The entire platform is built AI-first:
- **LangGraph** for complex multi-agent orchestration
- **RAG pipeline** for code-aware context retrieval
- **Model Router** for cost-optimized LLM selection
- **AI enrichment** for every analysis finding

### 4.4 Unified Workspace

Instead of juggling GitHub (code), Jira (tasks), Notion (docs), Slack (chat), and Copilot (AI), Kraivor provides a single workspace where all these concerns converge. A code change can be analyzed, discussed, documented, and tracked without leaving the platform.

### 4.5 Enterprise-Grade from Day One

Kraivor ships with:
- **Kubernetes manifests** for production deployment
- **Terraform modules** for AWS infrastructure
- **GitHub Actions CI/CD** with 7-job pipeline
- **Docker Compose** for local development
- **Postman collections** for API testing
- **Sentry** for error tracking
- **OpenTelemetry** for distributed tracing
- **Prometheus metrics** for observability

### 4.6 10-Language Support

While most analysis tools focus on 2-3 languages, Kraivor's `ChainedParser` supports 10 languages with language-specific AST parsing, rule engines, and anti-pattern detection.

---

## 5. System Architecture

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ┌───────────┐                               │
│                         │   Nginx    │  (API Gateway / Reverse Proxy)│
│                         │   :80/443  │                               │
│                         └─────┬─────┘                               │
│                               │                                      │
│          ┌────────────────────┼────────────────────┐                 │
│          │                    │                    │                 │
│          ▼                    ▼                    ▼                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐        │
│  │   Identity   │   │     Core     │   │    Frontend      │        │
│  │   :8001      │   │   :8002      │   │    :3000         │        │
│  │  Django DRF  │   │  Django DRF  │   │  Next.js 15      │        │
│  └──────┬───────┘   └──────┬───────┘   └──────────────────┘        │
│         │                  │                                         │
│         ▼                  ▼                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐        │
│  │   Analysis   │   │      AI      │   │  Notifications   │        │
│  │   :8003      │   │   :8004      │   │   :8005          │        │
│  │   FastAPI    │   │   FastAPI    │   │   FastAPI        │        │
│  └──────┬───────┘   └──────┬───────┘   └──────────────────┘        │
│         │                  │                                         │
│         ▼                  ▼                                         │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │                    Realtime :8006                        │        │
│  │               Node.js + Socket.io + Kafka                │        │
│  └─────────────────────────────────────────────────────────┘        │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────┐        │
│  │                Shared Infrastructure                     │        │
│  │  ┌──────────┐  ┌──────┐  ┌───────┐  ┌───────────────┐  │        │
│  │  │PostgreSQL│  │Redis │  │Kafka  │  │DynamoDB (chat)│  │        │
│  │  │   :5432  │  │:6379 │  │:9092  │  │   :8000       │  │        │
│  │  │+pgvector │  │      │  │       │  │               │  │        │
│  │  └──────────┘  └──────┘  └───────┘  └───────────────┘  │        │
│  └─────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Architecture Principles

| Principle | Implementation |
|-----------|---------------|
| **Single Entry Point** | All traffic routes through Nginx reverse proxy |
| **Async by Default** | Operations exceeding 500ms execute as background jobs (Celery + Kafka) |
| **Service Owns Its Data** | No cross-service database queries; inter-service communication via Kafka events or HTTP |
| **Fail Gracefully** | Each service degrades independently; circuit breakers for inter-service calls |
| **Everything Observable** | Correlation IDs propagate across services; structured logging; Prometheus metrics; Sentry errors |
| **Soft Deletes** | All entities retain audit trail via `deleted_at` timestamp |

### 5.3 Inter-Service Communication

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Service   │ ──Kafka──▶   Service   │ ──HTTP──▶   Service   │
│    A        │         │    B        │         │    C        │
└─────────────┘         └─────────────┘         └─────────────┘
       │                      │                       │
       │                 ┌────┴────┐                  │
       │                 │  Redis  │                  │
       │                 │ (Cache) │                  │
       │                 └─────────┘                  │
       └──────────────────────┬───────────────────────┘
                              │
                     ┌────────┴────────┐
                     │   PostgreSQL    │
                     │  (5 schemas)    │
                     └─────────────────┘
```

**Event Types Published to Kafka:**
- `AnalysisRequested` — Analysis service receives new analysis request
- `AnalysisCompleted` — Analysis service publishes results
- `AnalysisFailed` — Analysis service reports failure
- `NotificationRequired` — Core service emits notification events

**Synchronous Communication:**
- Identity service exposes JWKS endpoint for token verification
- Analysis service calls AI service for enrichment (HTTP)
- Core service verifies tokens via Identity service's JWKS endpoint

---

## 6. Microservices Breakdown

### 6.1 Identity Service (Django DRF — Port 8001)

**Purpose**: Authentication, user management, OAuth, API keys, profiles

**Django Apps:**
- `users` — User model with soft-delete, groups, permissions
- `authentication` — JWT (RS256), OAuth (GitHub/Google/Apple), refresh tokens
- `api_keys` — Scoped API key management
- `profiles` — User profiles with reputation system, follows

**Key Endpoints:**
- `POST /api/auth/register/` — User registration
- `POST /api/auth/login/` — Login (returns access + refresh JWT)
- `POST /api/auth/refresh/` — Refresh access token
- `GET /api/auth/jwks/` — JWKS public keys
- `POST /api/auth/oauth/{provider}/` — OAuth login/callback
- `POST /api/auth/mfa/verify/` — MFA verification
- `GET /api/profiles/{username}/` — Public profile
- `POST /api/api-keys/` — Create API key

**Security Features:**
- RS256 signed JWTs (asymmetric — private key signs, public key verifies)
- Refresh token rotation with device tracking
- OAuth tokens encrypted at rest (AES-256)
- API key hashing (SHA-256) with scoped permissions
- Rate limiting per user/IP
- Account lockout after failed attempts

---

### 6.2 Core Service (Django DRF — Port 8002)

**Purpose**: Workspaces, repositories, projects, tasks, knowledge spaces, community, chat, notifications, search

**Django Apps:**
- `workspaces` — Multi-tenant workspaces with membership, invitations, roles
- `repositories` — GitHub repository integration via GitHub App
- `knowledge` — Infinite canvas knowledge spaces with versioning
- `chat` — Team chat rooms, messages, participants
- `projects` — Project management with tasks, task links, priority/status
- `community` — Discussions, comments, voting, tags
- `notifications` — In-app notifications, FCM push tokens
- `search` — Full-text search via pg_trgm GIN indexes

**Key Entities:**
| Entity | Description |
|--------|-------------|
| `Workspace` | Multi-tenant container (plan: free/pro/team/enterprise) |
| `WorkspaceMember` | Role-based access (owner/admin/member/viewer) |
| `Repository` | Connected GitHub repo with analysis metadata |
| `KnowledgeSpace` | Infinite canvas for documentation (versioned) |
| `KnowledgeAsset` | Uploaded files stored in S3 |
| `Project` | Container for tasks with status/visibility |
| `Task` | Full task management with dependencies and estimates |
| `Discussion` | Community forum posts with voting |
| `Notification` | In-app notifications with 10 types |

**Background Workers (Celery):**
- `notifications` queue — Email sending, push notifications
- `default` queue — General async tasks
- `Celery Beat` — Scheduled tasks (cleanup, reminders)

**Kafka Consumer:**
- Consumes `AnalysisCompleted`, `AnalysisFailed` events
- Creates notifications for analysis results

---

### 6.3 Analysis Service (FastAPI — Port 8003)

**Purpose**: Code analysis engine — parsing, rules, scoring, simulation, reporting

**Architecture Pattern**: Clean Architecture / Domain-Driven Design

```
┌─────────────────────────────────────────────────────┐
│                    API Layer                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │  Health  │ │   Jobs   │ │ Findings │ │Reports │ │
│  │  Router  │ │  Router  │ │  Router  │ │ Router │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
├─────────────────────────────────────────────────────┤
│                  Application Layer                   │
│  ┌──────────────────────────────────────────────┐   │
│  │          Analysis Pipeline Handler            │   │
│  │  (16 stages: start→clone→parse→...→finalize) │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐   │
│  │ Commands │ │  Queries  │ │    UnitOfWork    │   │
│  └──────────┘ └──────────┘ └──────────────────┘   │
├─────────────────────────────────────────────────────┤
│                    Domain Layer                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ Entities │ │  Value   │ │Aggregates│ │Contracts│ │
│  │          │ │ Objects  │ │          │ │        │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
├─────────────────────────────────────────────────────┤
│                 Infrastructure Layer                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ DB Repos │ │  Scorer  │ │ Pipeline │ │  S3    │ │
│  │          │ │          │ │  Runner  │ │Client  │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
└─────────────────────────────────────────────────────┘
```

**Key Endpoints:**
- `POST /api/v1/jobs` — Trigger new analysis job
- `GET /api/v1/jobs/{id}` — Get job status and progress
- `GET /api/v1/jobs` — List jobs with filtering
- `GET /api/v1/findings` — Get analysis findings
- `GET /api/v1/findings/summary` — Aggregated summary
- `GET /api/v1/score-history/{repo_id}` — Score trends
- `GET /api/v1/reports/by-job/{id}` — Full report
- `GET /api/v1/enterprise-guide` — Enterprise report

---

### 6.4 AI Service (FastAPI — Port 8004)

**Purpose**: Multi-agent AI system with RAG pipeline, LLM routing, code embeddings

**Key Components:**
- **LangGraph Agent Graph** — 6-node orchestrator-specialist architecture
- **Model Router** — Routes to optimal LLM provider per task type
- **RAG Pipeline** — Semantic chunking + embeddings + pgvector retrieval
- **Usage Tracking** — Token counting, cost tracking, rate limiting
- **API Key Management** — User-managed LLM provider keys

**Key Endpoints:**
- `POST /api/v1/chat` — Chat completion with agent graph
- `POST /api/v1/embeddings` — Generate code embeddings
- `GET /api/v1/api-keys` — Manage LLM API keys
- `POST /api/v1/analysis` — AI-powered code analysis

---

### 6.5 Notifications Service (FastAPI — Port 8005 — Stubs)

**Purpose**: Email (AWS SES), Slack, push notifications

**Status**: Stubs only (Lambda variant implemented at `infra/lambda/notifications/main.py`)

**Delivery Channels:**
- **Email** — AWS SES with HTML templates
- **Slack** — Webhook-based Slack message posting
- **Push** — Firebase Cloud Messaging (FCM)
- **In-App** — Notifications stored in core service DB

---

### 6.6 Realtime Service (Node.js + Socket.io — Port 8006 — Stubs)

**Purpose**: WebSocket connections, presence, real-time updates

**Status**: Stubs only

**Architecture:**
- Socket.io server with Redis adapter for multi-instance scaling
- Kafka consumer for cross-service event streaming
- Room-based subscription management
- Presence tracking (online/offline/away)

---

### 6.7 Frontend (Next.js 15 — Port 3000)

**Purpose**: Web application, marketing site, admin dashboard

**Tech Stack:**
- **Framework**: Next.js 15 (App Router)
- **UI Library**: React 19 + shadcn/ui
- **Styling**: TailwindCSS with custom "krait-" design tokens (dark theme, venom-yellow accent)
- **State Management**: Zustand (persisted to localStorage)
- **API Client**: Axios (with token refresh interceptor + request queue) + native fetch
- **Real-time**: Socket.io client

**Route Structure:**
```
/                          → Marketing landing page
/login, /register, ...     → Authentication pages
/[workspace]/dashboard     → Workspace analytics dashboard
/[workspace]/analysis      → Analysis jobs and results
/[workspace]/ai            → AI chat interface
/[workspace]/chat          → Team chat
/[workspace]/community     → Discussions and forums
/[workspace]/inbox         → Notifications center
/[workspace]/knowledge     → Infinite canvas knowledge spaces
/[workspace]/projects      → Project management boards
/[workspace]/repositories  → Connected GitHub repositories
/[workspace]/settings      → Workspace settings
/[workspace]/profile       → User profiles
/[workspace]/tasks         → Task kanban board
```

---

## 7. Database Schema & Design

### 7.1 PostgreSQL (15 + pgvector + TimescaleDB)

**5 Schemas:**

```
kraivor
├── identity          # Auth service (users, OAuth, API keys, profiles)
├── core              # Core service (workspaces, repos, projects, chat, community)
├── analysis          # Analysis service (jobs, findings, scores, metrics)
├── ai                # AI service (embeddings, conversations, LLM config)
└── notifications     # Notification service (templates, logs)
```

### 7.2 DynamoDB (Chat History)

Used for chat message storage (NoSQL for high-volume write throughput):
- Partition key: `room_id`
- Sort key: `created_at`
- TTL-based auto-expiry for message retention

### 7.3 Redis (7用途)

| Use Case | Data Type | Eviction Policy |
|----------|-----------|-----------------|
| Celery Broker (AI) | List/Channel | N/A |
| Celery Result Backend | String | allkeys-lru |
| Cache (general) | String/Hash | allkeys-lru |
| Rate Limiting | Sorted Set | volatile-lru |
| Session Store | String | allkeys-lru |
| Socket.io Adapter | Pub/Sub | N/A |
| Job Locks | String (NX) | volatile-lru |

### 7.4 pgvector

The `ai.code_embeddings` table stores code embeddings for RAG:
- **Dimensions**: 384 (local SentenceTransformer) or 1536 (OpenAI text-embedding-3-small)
- **Index**: IVFFlat with cosine distance
- **Query**: `SELECT * FROM ai.code_embeddings ORDER BY embedding <=> $1 LIMIT $2`

### 7.5 TimescaleDB

The `analysis.score_history` table uses TimescaleDB hypertable for time-series score tracking:
- **Partition**: By `time` (1 day chunks)
- **Compression**: After 30 days
- **Retention**: 1 year

---

## 8. Authentication & Authorization

### 8.1 JWT Token Flow

```
┌──────┐          ┌──────────┐          ┌───────────┐
│Client│          │Identity  │          │PostgreSQL │
│      │          │ Service  │          │ (jwks)    │
└──┬───┘          └────┬─────┘          └─────┬─────┘
   │ POST /auth/login  │                      │
   │───────────────────▶│                      │
   │                   │ Verify credentials   │
   │                   │──────────────────────▶│
   │                   │◀──────────────────────│
   │                   │                      │
   │                   │ Sign JWT (RS256)     │
   │◀── {access, refresh} ────────────────────│
   │                   │                      │
   │ GET /api/resource │                      │
   │ (Authorization:   │                      │
   │  Bearer <access>) │                      │
   │───────────────────▶│                      │
   │                   │ Verify via JWKS      │
   │                   │──────────────────────▶│
   │                   │◀──────────────────────│
   │◀── 200 OK ────────│                      │
```

**Token Structure:**
- **Access Token**: Short-lived (15 minutes), contains user_id, scopes, workspace_ids
- **Refresh Token**: Long-lived (30 days), tracked per device, supports revocation

### 8.2 OAuth 2.0 Flow

**Supported Providers:** GitHub, Google, Apple

```
┌──────┐     ┌──────────┐     ┌──────────┐     ┌───────────┐
│Client│     │Identity  │     │OAuth     │     │   User    │
│      │     │ Service  │     │ Provider │     │  Browser  │
└──┬───┘     └────┬─────┘     └────┬─────┘     └─────┬─────┘
   │ Login with  │               │                  │
   │ GitHub      │               │                  │
   │─────────────▶│               │                  │
   │              │ Redirect to  │                  │
   │              │ OAuth URL    │                  │
   │◀── 302 ──────│──────────────│──────────────────│
   │              │               │                  │
   │ User authorizes              │                  │
   │─────────────────────────────────────────────────▶│
   │              │               │                  │
   │              │               │ Auth code        │
   │              │◀───────────────────────────────│
   │              │               │                  │
   │              │ Exchange code│                  │
   │              │──────────────▶│                  │
   │              │◀── tokens ────│                  │
   │              │               │                  │
   │              │ Encrypt &     │                  │
   │              │ store tokens │                  │
   │              │               │                  │
   │◀── JWT ──────│──────────────│──────────────────│
```

### 8.3 API Key Authentication

Used for CI/CD integration and programmatic access:
- Keys are generated with `secrets.token_urlsafe(32)`
- Stored as SHA-256 hash (never plaintext)
- Scoped: `analysis:read`, `analysis:write`, `workspace:admin`, etc.
- Rate limited per key

### 8.4 Role-Based Access Control (RBAC)

**Workspace Roles:**
| Role | Permissions |
|------|-------------|
| **Owner** | Full access, billing, delete workspace, transfer ownership |
| **Admin** | Full access except billing/deletion |
| **Member** | Read/write access to workspace resources |
| **Viewer** | Read-only access to analysis results and reports |

---

## 9. Analysis Pipeline & Engines

### 9.1 The 16-Stage Pipeline

```
START
  │
  ▼
CLONE ─────────── Clone git repository via GitHub API
  │
  ▼
PARSE ─────────── Parse codebase into AST (ChainedParser, 10 languages)
  │
  ▼
RULES ─────────── Apply rule registry (Security Engine)
  │
  ▼
SAVE_FINDINGS ─── Persist rule violations to database
  │
  ▼
DEAD_CODE ─────── Detect unused imports, functions, variables, classes
  │
  ▼
ERRORS ────────── Detect exception handling anti-patterns
  │
  ▼
RELIABILITY ───── Detect reliability anti-patterns (16 types)
  │
  ▼
MAINTAINABILITY ─ Compute maintainability metrics
  │
  ▼
DEVOPS ────────── Analyze Docker, CI/CD, K8s, Terraform configs
  │
  ▼
PERF ──────────── Estimate RPM, detect performance bottlenecks
  │
  ▼
SIMULATION ────── Load simulation at 100/500/5K/50K concurrent users
  │
  ▼
SCORE ─────────── Production Readiness Score (5 dimensions)
  │
  ▼
GUIDE_GEN ─────── Generate Enterprise Guide document
  │
  ▼
AI_ENRICH ─────── AI-powered enrichment of findings
  │
  ▼
FINALIZE ──────── Generate report PDF, upload to S3, emit event
  │
  ▼
END
```

Each stage is an independent handler with its own error handling. If a non-core stage fails, it is marked as `failed` but the pipeline continues. If a core engine (`security`, `maintainability`) fails, the pipeline stops and scoring is blocked.

### 9.2 The 8 Analysis Engines Explained

#### 9.2.1 Security Engine (Rules-Based)

**How It Works:**
- Uses a `RuleRegistry` loaded with language-specific security rules
- Each rule has: `id`, `category` (50 types), `severity`, `pattern` (AST-based), `message`, `recommendation`
- Applied against parsed AST from the `ChainedParser`
- Covers: OWASP Top 10, CWE categories, language-specific vulnerabilities

**What It Detects:**
- SQL injection (raw queries, string concatenation)
- Cross-Site Scripting (XSS)
- Command injection
- Path traversal
- Insecure deserialization
- Hardcoded secrets and credentials
- Weak cryptography
- Missing input validation
- Insecure direct object references (IDOR)

**Output:** `AnalysisResult` with category, severity, file location, code snippet, fix suggestion

---

#### 9.2.2 Dead Code Engine

**How It Works:**
- Parses AST to build a symbol reference graph
- Identifies entry points via decorator patterns (`@route`, `@app.`, `@celery`, `@task`, etc.)
- Traverses call graph from entry points
- Reports any unreachable symbols

**What It Detects:**
- **Unused imports** — Modules imported but never referenced
- **Unused functions** — Functions defined but never called
- **Unused variables** — Variables assigned but never read
- **Orphan classes** — Classes never instantiated or inherited
- **Unreachable code** — Code after `return`, `break`, `raise`, or always-false conditions
- **Dead branches** — If/else branches that can never execute

**Confidence Levels:**
- `high`: Confirmed unused (no references anywhere)
- `medium`: Likely unused (only referenced in tests or itself)
- `low`: Suspicious (few references, might be dynamically accessed)

---

#### 9.2.3 Error Detection Engine

**How It Works:**
- AST traversal looking for exception handling patterns
- Pattern matching for known anti-patterns
- Control flow analysis for error propagation

**What It Detects:**
- **Bare except clauses** — `except:` without specifying exception type
- **Swallowed exceptions** — Empty except blocks or `pass`
- **Missing timeouts** — External calls without timeout parameters
- **Silent failures** — Errors caught but not logged or re-raised
- **Overly broad exceptions** — `except Exception` when specific types needed
- **Missing finally blocks** — Resources not cleaned up on error

---

#### 9.2.4 Reliability Engine

**How It Works:**
- Analyzes 16 reliability anti-patterns via AST pattern matching
- Each pattern has configurable severity and confidence scoring
- Cross-file analysis for distributed system patterns

**What It Detects (16 patterns):**

| # | Anti-Pattern | Detection Method |
|---|--------------|-----------------|
| 1 | Missing retries | External calls without retry decorator/wrapper |
| 2 | Missing circuit breaker | No circuit breaker pattern around external services |
| 3 | Missing rollback | DB operations without transaction rollback |
| 4 | Transaction misuse | Nested transactions, long-running transactions |
| 5 | Race conditions | Shared state without locks in async contexts |
| 6 | Resource leaks | File handles, connections not in context managers |
| 7 | Infinite loops | While loops without break conditions |
| 8 | Thread safety violations | Shared mutable state without synchronization |
| 9 | Cache stampede | Cache miss without lock/mutex for regeneration |
| 10 | Idempotency issues | Side-effect operations without idempotency keys |
| 11 | Event ordering | Event-driven handlers assuming ordered delivery |
| 12 | Missing timeouts | Network calls without timeout configuration |
| 13 | Error swallowing | Caught exceptions with no action |
| 14 | Unawaited tasks | Async tasks created but not awaited |
| 15 | Connection pool misuse | Connections not returned to pool |
| 16 | Stale cache | Cache TTL too long without invalidation |

---

#### 9.2.5 Maintainability Engine

**How It Works:**
- Computes 14 maintainability metrics from AST analysis
- Uses standard software engineering formulas (Halstead, McCabe)
- Estimates technical debt in person-hours

**What It Detects & Computes:**

| Metric | Detection |
|--------|-----------|
| Long methods | Methods exceeding configurable line threshold |
| Too many parameters | Functions with 5+ parameters |
| High cyclomatic complexity | McCabe complexity > 10 |
| Deep nesting | Indentation depth > 4 levels |
| Duplicate code | Similar AST subtrees across files |
| Large classes | Classes exceeding 500 lines |
| Too many methods | Classes with 15+ methods |
| Long lines | Lines exceeding 120 characters |
| Missing docstrings | Public functions/classes without documentation |
| Magic numbers | Unexplained numeric literals |
| Empty catch blocks | Exception handlers with no body |
| TODO/FIXME markers | Comment analysis for incomplete work |
| Deep inheritance | Inheritance depth > 3 levels |
| Circular imports | Module dependency cycle detection |

**Outputs:**
- `MaintainabilityFindings` — Individual violations
- `MaintainabilityMetrics` — Aggregate: maintainability index, technical debt hours, complexity score

---

#### 9.2.6 DevOps Engine

**How It Works:**
- Parses DevOps configuration files (Dockerfile, docker-compose, CI/CD YAML, Terraform, Helm, K8s manifests, nginx configs)
- Each file type has a specialized analyzer
- Reports missing configurations and anti-patterns

**What It Analyzes:**

| Category | What It Checks |
|----------|---------------|
| **Dockerfile** | Multi-stage builds, layer caching, security scanning, non-root user, pinned versions, health checks |
| **Docker Compose** | Resource limits, restart policies, volume mounts, network configuration |
| **CI/CD** | Build caching, parallel jobs, artifact retention, secret management, environment promotion |
| **Terraform** | State locking, remote backend, provider versions, resource tagging, sensitive output |
| **Helm/K8s** | Resource requests/limits, liveness/readiness probes, pod anti-affinity, PDBs, network policies |
| **Nginx** | Rate limiting, SSL configuration, buffer sizes, upstream health checks |
| **Observability** | Structured logging configuration, metrics endpoints, trace sampling, alert rules |
| **Health Checks** | Existence and correctness of `/health` and `/ready` endpoints |
| **Environment** | .env.example completeness, secret management strategy, configuration validation |

---

#### 9.2.7 Performance Engine (RPM Calculator)

**How It Works:**
- Estimates Requests Per Minute (RPM) per endpoint
- Detects performance anti-patterns via AST analysis
- Computes latency percentiles (p50/p95/p99)
- Identifies bottleneck types and severity

**What It Detects:**
- **N+1 queries** — Loop-based database queries that should be batched
- **Synchronous external calls** — Blocking HTTP/socket calls in async context
- **Unbounded queries** — Database queries without LIMIT
- **Sync-in-async** — Synchronous operations inside async functions
- **File I/O in request path** — Disk operations during request handling
- **CPU complexity** — Computationally expensive operations (O(n²) or worse)
- **Memory pressure** — Large allocations without streaming or pagination
- **Serialization bottlenecks** — Large object serialization/deserialization
- **Missing caching** — Repeated computations that could be cached

**Performance Metrics Computed:**
- `estimated_rpm` per endpoint
- `p50_latency_ms` — Median latency
- `p95_latency_ms` — 95th percentile latency
- `p99_latency_ms` — 99th percentile latency
- `max_concurrent_users` — Maximum supported concurrency

---

#### 9.2.8 Simulation Engine (Production Simulator)

**How It Works:**
- Takes performance metrics from the Performance Engine
- Simulates load at 4 concurrency levels: 100, 500, 5,000, 50,000 concurrent users
- For each level, predicts: overall RPM, error rate, endpoint-level breakdown
- Identifies bottlenecks that emerge at scale

**Simulation Model:**

```
For each concurrency_level ∈ {100, 500, 5000, 50000}:
    error_rate = f(concurrent_users, endpoint_rpm, p99_latency)
    overall_rpm = sum(endpoint_rpm × capacity_factor)
    
    If error_rate < 1%:   status = "stable"
    If error_rate < 10%:  status = "degraded"  
    If error_rate ≥ 10%:  status = "failing"
    
    Record bottlenecks ordered by severity
```

**Output:** `SimulationResult` with:
- `status` — `stable`, `degraded`, or `failing`
- `overall_rpm` — Estimated throughput
- `error_rate_pct` — Estimated error percentage
- `endpoints_analysis` — Per-endpoint breakdown (JSONB)
- `bottlenecks` — Ordered list of system bottlenecks (JSONB)

---

### 9.3 Scoring System (ProductionReadinessScorer)

**5 Dimensions:**
1. **Performance Score** (0-100) — Based on RPM estimates, bottlenecks, simulation results
2. **Security Score** (0-100) — Based on vulnerability severity and count
3. **Reliability Score** (0-100) — Based on reliability anti-patterns
4. **Maintainability Score** (0-100) — Based on maintainability metrics
5. **DevOps Score** (0-100) — Based on DevOps configuration quality

**Overall Score Formula:**

```
overall_score = weighted_average(performance, security, reliability, maintainability, devops)

IF any_category < 50:
    overall_score = MIN(overall_score, category_with_lowest_score)
    [Critical-Floor Mechanism]
```

**Severity Penalties:**

| Severity | Penalty Points |
|----------|---------------|
| Critical | -15 |
| High | -10 |
| Medium | -5 |
| Low | -2 |
| Info | 0 |

**Capacity Penalties:**
- Simulation status `failing`: -50 points
- Simulation status `degraded`: -20 points

**Tier Classification:**

| Score Range | Tier | Label |
|-------------|------|-------|
| 0-29 | F | Critical |
| 30-49 | D | Needs Work |
| 50-69 | C | Fair |
| 70-84 | B | Good |
| 85-100 | A | Excellent |

---

## 10. AI System & LangGraph Agents

### 10.1 Multi-Agent Architecture

Kraivor's AI system uses **LangGraph's StateGraph** with an **orchestrator-specialist pattern**:

```
                    ┌──────────────┐
                    │  ORCHESTRATOR │  (Intent Classification)
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        Simple QA    Code Question    Complex Analysis
              │            │            │
              │            ▼            │
              │    ┌──────────────┐     │
              │    │   CONTEXT    │     │
              │    │  ASSEMBLER   │     │  (RAG Retrieval)
              │    └──────┬───────┘     │
              │           │             │
              │           ▼             │
              │    ┌──────────────┐     │
              │    │  CODE ANALYST│     │  (Code Review)
              │    └──────┬───────┘     │
              │           │             │
              │           ▼             │
              │    ┌──────────────┐     │
              │    │  SECURITY    │     │  (Vulnerability)
              │    │   ANALYST    │     │
              │    └──────┬───────┘     │
              │           │             │
              │           ▼             │
              │    ┌──────────────┐     │
              │    │ ARCHITECTURE │     │  (SOLID, Coupling)
              │    │   ANALYST    │     │
              │    └──────┬───────┘     │
              │           │             │
              │           ▼             │
              │    ┌──────────────┐     │
              │    │ PERFORMANCE  │     │  (Big-O, N+1)
              │    │   ANALYST    │     │
              │    └──────┬───────┘     │
              │           │             │
              └───────────┼─────────────┘
                          ▼
                   ┌──────────────┐
                   │  EXPLAINER   │  (Synthesis)
                   └──────┬───────┘
                          ▼
                         END
```

### 10.2 Agent Nodes

| Agent Node | Responsibility | LLM Model | Max Tokens |
|------------|---------------|-----------|------------|
| **Orchestrator** | Classifies intent: simple_qa vs multi-agent | gemini-flash-1.5 | 256 |
| **ContextAssembler** | Retrieves relevant code context via RAG | gemini-flash-1.5 | 1024 |
| **CodeAnalyst** | Code quality review, best practices | claude-3.5-sonnet | 4096 |
| **SecurityAnalyst** | Vulnerability analysis (CVSS-style) | claude-3.5-sonnet | 4096 |
| **ArchitectureAnalyst** | SOLID principles, coupling, cohesion | gpt-4o | 8192 |
| **PerformanceAnalyst** | Big-O, N+1, bottlenecks | claude-3.5-sonnet | 4096 |
| **Explainer** | Synthesizes all findings into final response | gemini-flash-1.5 | 2048 |

### 10.3 Model Router

The `ModelRouter` selects the optimal LLM per task based on:

1. **Task Type** (intent, code review, security, architecture, etc.)
2. **User Tier** (free → limited models, pro → mid-range, enterprise → all)
3. **Fallback Chain** (primary → fallback if primary fails)

**Task-to-Model Mapping:**

| Task | Primary | Fallback |
|------|---------|----------|
| `intent_classify` | Google Gemini Flash 1.5 | Groq Llama3-70b |
| `simple_qa` | Google Gemini Flash 1.5 | Groq Llama3-70b |
| `code_generation` | DeepSeek Coder | OpenAI GPT-4o-mini |
| `code_review` | Anthropic Claude 3.5 Sonnet | OpenAI GPT-4o-mini |
| `security_analysis` | Anthropic Claude 3.5 Sonnet | OpenAI GPT-4o |
| `architecture_review` | OpenAI GPT-4o | Claude 3.5 Sonnet |
| `performance_analysis` | Anthropic Claude 3.5 Sonnet | Google Gemini Pro 1.5 |
| `embeddings` | OpenAI text-embedding-3-small | None |

### 10.4 LLM Client Architecture

Supports 5 providers with unified interface:
- **OpenRouter** — Meta-router for 200+ models
- **Groq** — Ultra-low latency inference
- **OpenAI** — GPT-4 series
- **Anthropic** — Claude 3.5 series
- **Google Gemini** — Gemini Pro/Flash

**Provider-agnostic features:**
- Streaming support for all providers
- Token counting and cost tracking
- Automatic retry with exponential backoff
- Rate limit handling (429 responses)
- Timeout management

### 10.5 Usage Tracking

Each LLM call is logged to `ai.usage_logs`:
- User ID, provider, model
- Input/output token counts
- Cost (computed from token counts × provider pricing)
- Latency (milliseconds)
- Prometheus metrics counters

---

## 11. RAG Pipeline (Retrieval-Augmented Generation)

### 11.1 Architecture

```
Source Code
    │
    ▼
┌──────────────┐
│  Semantic    │  Code-aware chunking
│  Chunker     │  (AST-based + token fallback)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Embedder    │  Local: SentenceTransformer (384d)
│              │  OpenAI: text-embedding-3-small (1536d)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  pgvector    │  Cosine similarity search
│  Retriever   │  (IVFFlat index)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Context     │  Assembled for LLM
│  Assembly    │
└──────────────┘
```

### 11.2 Semantic Chunker

**Strategy:**
1. **AST-based chunking** — Uses tree-sitter to parse source code into AST
   - Supported languages: Python, JavaScript, TypeScript
   - Chunks at function/class boundaries
   - Preserves imports and module-level context
2. **Token-based fallback** — For unsupported languages
   - `tiktoken` with `cl100k_base` encoding
   - Chunk size: 500 tokens
   - Overlap: 50 tokens

**Output:** List of `Document` objects with:
- `content` (truncated to 2000 chars for storage)
- `metadata`: file_path, language, line_start, line_end

### 11.3 Embedder

**Two modes:**
| Mode | Model | Dimensions | Use Case |
|------|-------|-----------|----------|
| **Local** | SentenceTransformer (`all-MiniLM-L6-v2`) | 384 | Development, no API cost |
| **OpenAI** | text-embedding-3-small | 1536 | Production, higher accuracy |

### 11.4 Retriever

**Query Flow:**
```
query_embedding = embedder.embed(user_query)

results = db.query("""
    SELECT * FROM ai.code_embeddings
    WHERE repo_id = ANY(:repo_ids)
      AND workspace_id = :workspace_id
      AND embedding <=> :query_embedding < :threshold
    ORDER BY embedding <=> :query_embedding
    LIMIT :top_k
""")
```

- **Similarity metric**: Cosine distance (`<=>` operator)
- **Threshold**: `min_score = 0.5` (configurable)
- **Filtering**: By repo_ids and workspace_id
- **Top-K**: Configurable (default: 5)

### 11.5 Indexing Pipeline

```
┌──────────────┐
│  Index Job   │  Created when repo is connected
│  (ai.index_  │
│   jobs)      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  File Scan   │  Iterate source files
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Chunking    │  SemanticChunker
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Embedding   │  Embedder
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Storage     │  Upsert to pgvector
└──────────────┘
```

---

## 12. Technology Stack — Tools Deep Dive

### 12.1 LangChain

**Where Used:** AI Service (`services/ai/`)

**What It Does:** LangChain is used as the foundational framework for building the LLM-powered applications. It provides:
- **Chat model abstractions** — Unified interface across OpenAI, Anthropic, Google, Groq, OpenRouter
- **Prompt templates** — Structured prompts for each agent node
- **Output parsers** — Structured response parsing from LLM outputs
- **Callbacks** — Streaming, token counting, and metrics collection
- **RAG primitives** — Document loaders, text splitters, vector store integrations

**Why Kraivor Uses It:**
- Provider-agnostic LLM integration reduces vendor lock-in
- Built-in streaming support for real-time chat experience
- Prompt template management for consistent agent behavior
- Extensible callback system for monitoring and cost tracking

**Where Specifically:**
- `services/ai/app/domain/contracts/llm.py` — Abstract LLM client interface
- `services/ai/app/infrastructure/llm/` — Concrete implementations for each provider
- `services/ai/app/application/agents/` — Agent node prompts and output parsing

---

### 12.2 LangGraph

**Where Used:** AI Service (`services/ai/app/application/agents/graph.py`)

**What It Does:** LangGraph extends LangChain to build stateful, multi-agent applications as graphs. Each node is a computation step, and edges define the flow of control with conditional routing.

**Why Kraivor Uses It:**
- **Stateful agent orchestration** — Maintains conversation state across agent nodes
- **Conditional routing** — Orchestrator decides which specialists to invoke based on intent
- **Cyclic graph support** — Agents can loop back for refinement
- **Parallel execution** — Multiple specialist agents can run concurrently
- **Persistence** — Graph state can be persisted for conversation history

**The Agent Graph:**
```python
graph = StateGraph(AgentState)
graph.add_node("orchestrator", OrchestratorNode())
graph.add_node("context_assembler", ContextAssemblerNode())
graph.add_node("code_analyst", CodeAnalystNode())
graph.add_node("security_analyst", SecurityAnalystNode())
graph.add_node("architecture_analyst", ArchitectureAnalystNode())
graph.add_node("performance_analyst", PerformanceAnalystNode())
graph.add_node("explainer", ExplainerNode())

graph.set_entry_point("orchestrator")
graph.add_conditional_edges("orchestrator", route_orchestrator, {...})
graph.add_conditional_edges("context_assembler", route_context, {...})
# ... more edges

app = graph.compile()
```

**Routing Logic:**
- Simple questions → bypass specialists, go to explainer
- Code questions → context_assembler → code_analyst → specialists
- Complex analysis → all specialists in sequence

---

### 12.3 RAG (Retrieval-Augmented Generation)

**Where Used:** AI Service — ContextAssembler node + RAG pipeline

**What It Does:** RAG enhances LLM responses by retrieving relevant code context before generating answers. Instead of relying solely on training data, the AI searches the actual codebase for relevant snippets.

**Why Kraivor Uses It:**
- **Code-aware answers** — AI understands the actual codebase, not just general knowledge
- **Up-to-date context** — Always retrieves from the latest indexed code
- **Reduced hallucinations** — Grounds AI responses in actual source code
- **Project-specific insights** — Understands project conventions, naming, architecture

**Pipeline Components:**
1. `SemanticChunker` — Code-aware document splitting (AST + token-based)
2. `Embedder` — Vector embedding generation (local or OpenAI)
3. `Indexer` — Store embeddings in pgvector
4. `Retriever` — Cosine similarity search at query time

---

### 12.4 Celery

**Where Used:** Core Service (`services/core/`), AI Service (`services/ai/app/core/celery_app.py`)

**What It Does:** Celery is a distributed task queue for asynchronous job processing.

**Why Kraivor Uses It:**
- **Background processing** — Long-running tasks (analysis, indexing) don't block API responses
- **Task retries** — Automatic retry with exponential backoff for failed tasks
- **Scheduled tasks** — Celery Beat for periodic maintenance (cleanup, health checks)
- **Task prioritization** — Multiple queues for different priority levels
- **Result backend** — Redis-backed result storage for task status queries

**Queues:**
| Queue | Service | Purpose |
|-------|---------|---------|
| `ai.inference` | AI | LLM inference tasks |
| `ai.indexing` | AI | Code embedding/indexing jobs |
| `ai.maintenance` | AI | Periodic maintenance (cache cleanup) |
| `notifications` | Core | Email and push notification dispatch |
| `default` | Core | General async tasks |

**Configuration:**
```python
celery_app.conf.update(
    task_acks_late=True,          # Re-deliver if worker crashes
    worker_prefetch_multiplier=1, # One task at a time per worker
    task_time_limit=600,          # Max 10 minutes per task
    task_soft_time_limit=300,     # 5-minute soft limit
    task_track_started=True,      # Track task start time
)
```

---

### 12.5 Redis

**Where Used:** Every service

**What It Does:** Redis is an in-memory data structure store used as cache, message broker, and session store.

**Why Kraivor Uses It:**
- **Celery Broker** — Message queue for task distribution to workers
- **Celery Result Backend** — Stores task results for status queries
- **General Cache** — Redis-accelerated database query results
- **Rate Limiting** — Sliding window rate limiting via sorted sets
- **Session Store** — Distributed session storage across service instances
- **Job Locks** — Distributed locks to prevent duplicate job execution
- **Socket.io Adapter** — Multi-instance WebSocket message broadcasting

**Configuration:**
```yaml
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

---

### 12.6 DynamoDB

**Where Used:** Core Service — Chat history storage

**What It Does:** Amazon DynamoDB is a fully managed NoSQL key-value and document database.

**Why Kraivor Uses It:**
- **Chat history** — High-volume write throughput for real-time messaging
- **Serverless scaling** — No manual sharding or capacity planning
- **TTL-based expiry** — Automatic message retention management
- **Low-latency queries** — Single-digit millisecond access patterns
- **Cost-effective** — Pay-per-request pricing for variable workloads

**Schema:**
```
Table: chat_messages
  PK: room_id (String)
  SK: created_at (ISO8601 String)
  Attributes: user_id, content, message_type, metadata
  TTL: expires_at
```

**Local Development:** Uses DynamoDB Local Docker image for offline development.

---

### 12.7 pgvector

**Where Used:** AI Service — Code embeddings storage and retrieval

**What It Does:** pgvector is a PostgreSQL extension that adds vector similarity search capabilities directly in the database.

**Why Kraivor Uses It:**
- **Single database** — No separate vector database infrastructure needed
- **ACID compliance** — Vector operations benefit from PostgreSQL's transactional guarantees
- **SQL integration** — Seamless joins with other tables (repos, users, workspaces)
- **IVFFlat indexing** — Approximate nearest neighbor search for fast retrieval
- **Cost savings** — Eliminates need for dedicated vector DB (Pinecone, Weaviate, etc.)

**Schema:**
```sql
CREATE TABLE ai.code_embeddings (
    id UUID PRIMARY KEY,
    repo_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    file_path TEXT NOT NULL,
    language TEXT,
    content TEXT,
    embedding vector(1536),  -- or vector(384) for local
    line_start INTEGER,
    line_end INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_code_embeddings_embedding
    ON ai.code_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

---

### 12.8 AWS S3

**Where Used:** Analysis Service, Core Service

**What It Does:** Amazon S3 is object storage for files and artifacts.

**Why Kraivor Uses It:**
- **Analysis reports** — Generated PDF reports stored for download
- **Knowledge assets** — User-uploaded files (images, PDFs, documents) in knowledge spaces
- **Code archives** — Repository snapshots for analysis
- **Export files** — Workspace data exports
- **Glacier lifecycle** — Cost-effective archival for old reports

**Bucket Structure:**
```
s3://kraivor-reports/          → Analysis reports
s3://kraivor-archives/         → Code archives
s3://kraivor-exports/          → Data exports
s3://kraivor-assets/           → Knowledge space uploads
```

---

### 12.9 AWS Lambda

**Where Used:** Notifications (`infra/lambda/notifications/`)

**What It Does:** AWS Lambda is serverless compute for event-driven functions.

**Why Kraivor Uses It:**
- **Notification dispatch** — Event-driven email/Slack/push notification delivery
- **Cost-effective** — Pay only per invocation, no idle cost
- **Auto-scaling** — Handles notification spikes without provisioning
- **SQS integration** — Triggered via SQS queue for reliable delivery

**Lambda Function:**
```python
# Notification dispatcher (Python 3.11)
# Routes: email → SES, Slack → webhook, push → FCM
def handler(event, context):
    for record in event['Records']:
        notification = json.loads(record['body'])
        dispatch(notification)
```

---

### 12.10 GitHub App

**Where Used:** Core Service (`core.apps.repositories`)

**What It Does:** A GitHub App that integrates Kraivor directly with GitHub repositories.

**Why Kraivor Uses It:**
- **Automated repository access** — Installed at org/repo level, auto-syncs repositories
- **Webhook events** — Receives push, pull request, and installation events
- **Check runs** — Posts analysis results as GitHub Check Runs (PR status)
- **Commit statuses** — Updates commit status with analysis results
- **Seamless UX** — No manual token management for users

**Installation Flow:**
1. User clicks "Connect GitHub" in Kraivor
2. Redirected to GitHub App install URL
3. User selects org/repos to grant access
4. GitHub sends installation webhook to Kraivor
5. Kraivor syncs all accessible repositories
6. Auto-analyzes new pushes and PRs

**Data Synced:**
- Repository metadata (name, description, language, visibility)
- Default branch
- Pull request events
- Push events (trigger analysis)

---

### 12.11 GitHub OAuth

**Where Used:** Identity Service (`auth.apps.authentication`)

**What It Does:** GitHub OAuth allows users to sign in to Kraivor using their GitHub account.

**Why Kraivor Uses It:**
- **Frictionless onboarding** — No new account creation for GitHub users
- **Trust & familiarity** — Users trust GitHub's authentication
- **Profile data** — Auto-populates name, avatar, email from GitHub
- **Developer audience** — GitHub is the primary identity provider for developers

**Flow:**
1. User clicks "Sign in with GitHub"
2. Redirected to `https://github.com/login/oauth/authorize`
3. User authorizes Kraivor
4. GitHub redirects back with authorization code
5. Kraivor exchanges code for access token
6. Fetches user profile from GitHub API
7. Creates/updates local user, issues JWT

---

### 12.12 Google OAuth

**Where Used:** Identity Service (`auth.apps.authentication`)

**What It Does:** Google OAuth provides sign-in via Google accounts.

**Why Kraivor Uses It:**
- **Broad reach** — Every email user has a Google account
- **Enterprise adoption** — Google Workspace orgs prefer Google SSO
- **Profile enrichment** — Auto-fills name, email, avatar

---

### 12.13 WebSocket

**Where Used:** Core Service (Django Channels), Realtime Service (Socket.io — planned)

**What It Does:** WebSocket provides full-duplex communication channels over a single TCP connection.

**Why Kraivor Uses It:**
- **Analysis progress** — Real-time job status updates during analysis
- **Live notifications** — Push notifications without polling
- **Team chat** — Instant message delivery
- **Collaborative editing** — Real-time canvas updates in knowledge spaces

**Nginx Configuration:**
```nginx
location /ws/ {
    proxy_pass http://core;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400s;
}
```

---

### 12.14 Sentry

**Where Used:** All services (configured via environment variables)

**What It Does:** Sentry is an error tracking and performance monitoring platform.

**Why Kraivor Uses It:**
- **Real-time error alerts** — Instant notification of production errors
- **Breadcrumbs** — Context-rich error reports with request traces
- **Performance monitoring** — Transaction tracing for API latency analysis
- **Release tracking** — Correlate errors with specific deployments
- **User feedback** — Collect user-reported issues

**Configuration:**
```env
SENTRY_DSN=https://...@oXXXX.ingest.sentry.io/XXXXXX
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.2  # Sample 20% of transactions
```

---

### 12.15 Apache Kafka

**Where Used:** All services (event bus)

**What It Does:** Kafka is a distributed event streaming platform for building real-time data pipelines.

**Why Kraivor Uses It:**
- **Cross-service events** — Decoupled communication between microservices
- **Event sourcing** — Audit trail of all analysis requests and completions
- **Buffering** — Handles traffic spikes by queuing events
- **Replay capability** — Re-process events for debugging or recovery
- **Multiple consumers** — Both core service and realtime service consume analysis events

**Topics:**
| Topic | Producer | Consumers | Message Type |
|-------|----------|-----------|-------------|
| `analysis.requested` | Analysis Service | Core, Realtime | Analysis job started |
| `analysis.completed` | Analysis Service | Core, Realtime | Analysis results ready |
| `analysis.failed` | Analysis Service | Core, Realtime | Analysis job failed |
| `notification.required` | Core Service | Notifications | Send notification |

---

### 12.16 Docker & Docker Compose

**Where Used:** Development and production deployment

**What It Does:** Containerization platform for consistent environments.

**Services in Docker Compose:**
1. `postgres` — PostgreSQL 15 with health checks and tuning
2. `redis` — Redis 7 with AOF persistence
3. `kafka` — Apache Kafka 3.9 (KRaft mode, no Zookeeper)
4. `identity` — Django DRF auth service
5. `core` — Django DRF core service
6. `analysis` — FastAPI analysis service
7. `ai` — FastAPI AI service
8. `core-worker` — Celery worker for async tasks
9. `core-beat` — Celery beat for scheduled tasks
10. `core-consumer` — Kafka consumer for cross-service events
11. `dynamodb-local` — DynamoDB Local for chat history
12. `frontend` — Next.js 15 application
13. `nginx` — Nginx reverse proxy

**Notable Health Checks:**
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- Kafka: topic listing
- Each Python service: `/api/health/` HTTP endpoint

---

### 12.17 Terraform

**Where Used:** Infrastructure (`infra/terraform/`)

**Modules:**
| Module | Resources | Purpose |
|--------|-----------|---------|
| **eks** | EKS cluster + IAM role | Kubernetes control plane |
| **rds** | RDS PostgreSQL instance | Database (db.r6g.large prod) |
| **elasticache** | ElastiCache Redis cluster | Caching (cache.r6g.large prod) |
| **s3** | S3 buckets | Reports, archives, exports |
| **sqs** | SQS queue + DLQ | Notification event queue |
| **lambda-notifications** | Lambda function | Serverless notification dispatch |

**Environments:**
- `dev` — Smaller instances (db.t3.micro, cache.t3.micro)
- `prod` — Production-grade instances

---

### 12.18 Kubernetes (EKS)

**Where Used:** Production deployment (`infra/kubernetes/`)

**Deployments (7) in `kraivor-prod` namespace:**

| Deployment | Replicas | CPU (req/lim) | Memory (req/lim) |
|-----------|----------|---------------|-------------------|
| identity | 3 | 250m/500m | 256Mi/512Mi |
| core | 3 | 250m/500m | 256Mi/512Mi |
| analysis | 2 | 500m/1000m | 512Mi/1Gi |
| ai | 2 | 500m/1000m | 512Mi/1Gi |
| frontend | 2 | 250m/500m | 256Mi/512Mi |
| notifications | 1 | default | default |
| realtime | 1 | default | default |

**Features:**
- Horizontal Pod Autoscaler (HPA) for auto-scaling
- Readiness and liveness probes
- Resource requests and limits
- Rolling update strategy

---

### 12.19 GitHub Actions CI/CD

**Where Used:** `.github/workflows/`

**Workflow Jobs (7):**
1. **test-auth** — Django tests for identity service
2. **lint** — Flake8 across all Python services
3. **test-core** — Django tests for core service
4. **analysis-lint** — Ruff lint for analysis service
5. **analysis-test** — Pytest for analysis service
6. **security-checks** — Safety (dependency vulns) + Bandit (code security)
7. **deploy** (main branch only) — Build Docker images → Push to ECR → Deploy to EKS

---

### 12.20 TimescaleDB

**Where Used:** Analysis Service — Score history

**What It Does:** TimescaleDB is a time-series database extension for PostgreSQL.

**Why Kraivor Uses It:**
- **Time-series optimization** — Auto-partitioning by time for score history
- **Continuous aggregates** — Pre-computed daily/weekly score averages
- **Data compression** — Reduces storage for historical data
- **Retention policies** — Automatic data pruning after configurable period

---

### 12.21 MinIO (S3-Compatible Storage)

**Where Used:** Local development S3 replacement (`docker-compose.yml`)

**What It Does:** MinIO is an S3-compatible object storage server for local development.

**Why Kraivor Uses It:**
- **Local S3 emulation** — Test file uploads without AWS credentials
- **S3 API compatibility** — Uses same SDK, switches to real S3 in production
- **Console UI** — Web interface for browsing uploaded files

---

### 12.22 OpenTelemetry

**Where Used:** All services (configured via environment)

**What It Does:** OpenTelemetry provides distributed tracing and metrics collection.

**Why Kraivor Uses It:**
- **Distributed tracing** — Trace requests across all microservices
- **Correlation IDs** — Propagate context through service boundaries
- **Vendor-neutral** — Export traces to any backend (Jaeger, Zipkin, Datadog)
- **Automatic instrumentation** — Framework-level span creation

---

### 12.23 Prometheus

**Where Used:** AI Service (metrics endpoint)

**What It Does:** Prometheus is a monitoring system with a dimensional data model.

**Why Kraivor Uses It:**
- **LLM metrics** — Track calls, duration, cost, tokens per model/provider
- **Service health** — Request rates, error rates, latency histograms
- **Custom metrics** — Analysis job counts, queue depths, cache hit rates

**AI Service Metrics:**
```python
llm_calls_total = Counter("llm_calls_total", "Total LLM calls", ["provider", "model"])
llm_duration_seconds = Histogram("llm_duration_seconds", "LLM call duration", ["provider"])
llm_cost_total = Counter("llm_cost_total", "Total LLM cost (USD)", ["provider", "model"])
llm_tokens_total = Counter("llm_tokens_total", "Total tokens", ["provider", "type"])
```

---

## 13. Comparison with Existing Developer Platforms

### 13.1 Kraivor vs. GitHub

| Dimension | GitHub | Kraivor |
|-----------|--------|---------|
| **Primary Function** | Code hosting, version control, collaboration | Production intelligence, code analysis, AI insights |
| **Code Analysis** | Dependabot (dependencies), CodeQL (security) | Full Production Readiness Score (5 dimensions) |
| **AI Features** | Copilot (code completion) | Multi-agent AI with RAG, code review, architecture analysis |
| **Project Management** | GitHub Issues (basic) | Full project management with tasks, priorities, estimates |
| **Documentation** | GitHub Wiki (basic) | Knowledge Spaces (infinite canvas, versioned) |
| **Community** | Discussions (basic) | Full discussion platform with voting, reputation |
| **Production Simulation** | ❌ Not available | ✅ Load simulation at 100-50K users |
| **Deployment Analysis** | ❌ Not available | ✅ DevOps readiness check (Docker, K8s, Terraform) |
| **Scoring** | Security score (Dependabot) | Multi-dimensional Production Readiness Score |
| **Integration** | Third-party via GitHub Apps | Built-in analysis, no external tools needed |

**Verdict:** GitHub is the world's best code hosting platform. Kraivor complements it as a deep analysis and intelligence layer — not a replacement.

---

### 13.2 Kraivor vs. Linear

| Dimension | Linear | Kraivor |
|-----------|--------|---------|
| **Primary Function** | Issue tracking, project management | Full developer intelligence platform |
| **Speed** | Extremely fast, keyboard-first | Comparable performance |
| **Issue Tracking** | Excellent, intuitive | Full-featured with task links, dependencies |
| **Roadmaps** | Built-in | Project-based organization |
| **Code Integration** | GitHub/GitLab sync (basic) | Deep GitHub integration with analysis |
| **AI Features** | Linear AI (issue writing assistance) | Multi-agent AI for code analysis, review, architecture |
| **Code Analysis** | ❌ Not available | ✅ Full 8-engine analysis pipeline |
| **Knowledge Management** | ❌ Not available | ✅ Infinite canvas knowledge spaces |
| **Community/Discussions** | ❌ Not available | ✅ Built-in discussion platform |
| **Production Simulation** | ❌ Not available | ✅ Load simulation and bottleneck detection |
| **Scoring** | ❌ Not available | ✅ Production Readiness Score |

**Verdict:** Linear excels at issue tracking speed and UX. Kraivor provides a broader platform where issues are connected to actual code quality and production readiness.

---

### 13.3 Kraivor vs. Jira

| Dimension | Jira | Kraivor |
|-----------|------|---------|
| **Primary Function** | Issue tracking, Agile project management | Developer intelligence platform |
| **Customization** | Extremely high (workflows, fields, screens) | Focused, opinionated workflows |
| **Complexity** | High learning curve, often over-engineered | Clean, developer-friendly UX |
| **Code Analysis** | ❌ Not built-in (third-party addons) | ✅ Built-in 8-engine analysis pipeline |
| **AI Features** | Atlassian Intelligence (basic) | Multi-agent AI with RAG, code context |
| **Knowledge Management** | Confluence (separate product) | Knowledge Spaces (integrated) |
| **Code Integration** | GitHub/GitLab connector | Deep GitHub App integration |
| **Real-time Chat** | ❌ Not built-in | ✅ Built-in team chat |
| **Scoring** | ❌ Not available | ✅ Production Readiness Score |
| **Deployment Analysis** | ❌ Not available | ✅ DevOps readiness check |
| **Pricing** | Expensive per-user | Competitive, tiered pricing |

**Verdict:** Jira is the enterprise standard for issue tracking. Kraivor offers a more focused, developer-centric experience with deep code intelligence that Jira cannot match without multiple addons.

---

### 13.4 Kraivor vs. SonarQube

| Dimension | SonarQube | Kraivor |
|-----------|-----------|---------|
| **Primary Function** | Code quality and security analysis | Production intelligence platform |
| **Analysis Depth** | Static analysis (linting, bugs, vulns) | Static + dynamic (load simulation, performance estimation) |
| **Languages** | 30+ languages | 10 languages (depth over breadth) |
| **Scoring** | Quality Gate (pass/fail) | Production Readiness Score (0-100, 5 dimensions) |
| **AI Integration** | ❌ Minimal | ✅ Multi-agent AI with RAG |
| **Load Simulation** | ❌ Not available | ✅ 100-50K concurrent user simulation |
| **DevOps Analysis** | ❌ Not available | ✅ Docker, K8s, Terraform, CI/CD analysis |
| **Performance Estimation** | ❌ Not available | ✅ RPM, latency, bottleneck detection |
| **Knowledge Management** | ❌ Not available | ✅ Knowledge spaces, discussions |
| **Project Management** | ❌ Not available | ✅ Tasks, projects, priorities |
| **Team Collaboration** | ❌ Not available | ✅ Chat, community, notifications |

**Verdict:** SonarQube is the gold standard for static analysis. Kraivor goes beyond into production simulation, performance estimation, and team collaboration — areas SonarQube doesn't address.

---

### 13.5 Kraivor vs. CodeRabbit / AI Code Review Tools

| Dimension | CodeRabbit | Kraivor |
|-----------|-----------|---------|
| **Primary Function** | AI code review on PRs | Full production intelligence platform |
| **AI Review** | PR-level code review | Multi-agent analysis + RAG + simulation |
| **Analysis Depth** | Code review comments | 8 engines across 5 dimensions |
| **Production Simulation** | ❌ Not available | ✅ Load testing simulation |
| **Scoring** | ❌ Not available | ✅ Production Readiness Score |
| **Project Management** | ❌ Not available | ✅ Tasks, projects, roadmaps |
| **Knowledge Management** | ❌ Not available | ✅ Knowledge spaces |
| **Team Chat** | ❌ Not available | ✅ Built-in |
| **Deployment Analysis** | ❌ Not available | ✅ DevOps readiness |

**Verdict:** CodeRabbit does one thing well: AI-powered PR reviews. Kraivor is a comprehensive platform with AI as one component of a larger intelligence system.

---

### 13.6 Kraivor vs. Notion / Confluence

| Dimension | Notion / Confluence | Kraivor |
|-----------|-------------------|---------|
| **Primary Function** | Documentation, wikis, knowledge base | Developer intelligence platform |
| **Code Integration** | Code blocks (manual) | Deep code analysis integration |
| **AI Features** | AI writing assistant | Multi-agent AI with code context |
| **Code Analysis** | ❌ Not available | ✅ 8-engine pipeline |
| **Production Insights** | ❌ Not available | ✅ Scores, simulation, bottlenecks |
| **Developer Focus** | General purpose | Purpose-built for developers |

**Verdict:** Notion/Confluence are excellent documentation tools. Kraivor's knowledge spaces are purpose-built for developer documentation with deep code integration.

---

### 13.7 Kraivor vs. Linear + SonarQube + Notion + Slack (Combined)

| Dimension | Fragmented Stack | Kraivor |
|-----------|-----------------|---------|
| **Setup Complexity** | 4+ separate tools to configure, integrate, and maintain | Single platform |
| **Context Switching** | Constant app switching | Unified workspace |
| **Cost** | 4+ separate subscriptions | Single subscription |
| **Integration Depth** | Shallow API-based integrations | Deep, built-in connections |
| **Search** | Search each tool separately | Unified search across all data |
| **User Management** | 4+ user directories | Single user database |
| **Data Consistency** | Duplicate/conflicting data across tools | Single source of truth |

**Verdict:** The fragmented stack is the current reality for most teams. Kraivor's value proposition is eliminating the overhead of maintaining and switching between multiple tools while providing deeper integration than any API-based approach can achieve.

---

## 14. Infrastructure & Deployment

### 14.1 Local Development

```bash
# Prerequisites
docker --version     # Docker 24+
docker-compose --version  # Docker Compose v2
python --version     # Python 3.11+
node --version       # Node 18+

# One-time setup
cp .env.example .env
# Edit .env with your API keys

# Start all services
make dev
# OR: docker-compose --profile dev up --build -d

# Run tests
make test

# View logs
make logs

# Stop
make stop
```

### 14.2 Production Deployment (AWS EKS)

**Infrastructure Provisioning:**
```bash
cd infra/terraform/environments/prod
terraform init
terraform plan
terraform apply
```

**Application Deployment:**
```bash
# Build and push Docker images
docker build -t kraivor/identity:latest ./services/auth
docker tag kraivor/identity:latest $ECR_REPO/identity:latest
docker push $ECR_REPO/identity:latest

# Deploy to EKS
kubectl apply -f infra/kubernetes/
```

### 14.3 CI/CD Pipeline

```
Git Push (main)
    │
    ▼
┌─────────────────────────────────────────────────────┐
│              GitHub Actions Workflow                  │
├─────────────────────────────────────────────────────┤
│  1. test-auth      → Django tests (identity)         │
│  2. lint           → Flake8 (all Python)             │
│  3. test-core      → Django tests (core)             │
│  4. analysis-lint  → Ruff (analysis service)         │
│  5. analysis-test  → Pytest (analysis service)       │
│  6. security-checks→ Safety + Bandit                 │
├─────────────────────────────────────────────────────┤
│  7. deploy (main only)                               │
│     → Build Docker images                            │
│     → Push to Amazon ECR                             │
│     → Deploy to Amazon EKS                           │
└─────────────────────────────────────────────────────┘
```

---

## 15. Production-Level User Management

### 15.1 User Lifecycle

```
                    ┌──────────────┐
                    │  Registration│
                    │ (Email/OAuth)│
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Email        │
                    │ Verification │
                    └──────┬───────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Onboarding   │
                    │ (Workspace   │
                    │  Creation)   │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Solo     │ │ Invited  │ │Enterprise│
        │ Workspace│ │ to Team  │ │ SSO      │
        └──────────┘ └──────────┘ └──────────┘
              │            │            │
              ▼            ▼            ▼
        ┌──────────────────────────────────┐
        │       Active User                 │
        │  (Analysis, AI, Projects, Chat)   │
        └──────────────────────────────────┘
              │
              ▼
        ┌──────────────┐
        │ Deletion /   │
        │ Soft-Delete  │
        └──────────────┘
```

### 15.2 Multi-Tenancy

**Workspace Isolation:**
- Each workspace has its own UUID
- All entities reference `workspace_id`
- PostgreSQL RLS (Row-Level Security) for data isolation
- Cross-workspace data access prevented at application layer

**Plan Tiers:**
| Tier | Max Members | Analysis Limits | AI Model Access | Storage |
|------|-------------|-----------------|-----------------|---------|
| Free | 1 | 5 analyses/month | Gemini Flash only | 100MB |
| Pro | 10 | 100 analyses/month | Claude + GPT-4o-mini | 5GB |
| Team | Unlimited | Unlimited | All models | 50GB |
| Enterprise | Unlimited | Unlimited + custom | All models + custom | Custom |

### 15.3 Session Management

- **Access Tokens**: 15-minute expiry, stored in memory (client)
- **Refresh Tokens**: 30-day expiry, stored in HTTP-only cookie + DB
- **Device Tracking**: Each refresh token tied to device_name, device_type, IP, user_agent
- **Revocation**: Admin can revoke all sessions for a user
- **Concurrent Sessions**: Configurable limit (default: 10)

### 15.4 Rate Limiting

| Endpoint Type | Rate Limit | Window |
|--------------|------------|--------|
| Auth endpoints | 10 requests/min | Per IP |
| API endpoints | 100 requests/min | Per API key |
| Analysis triggers | 5 requests/min | Per workspace |
| AI chat | 30 messages/min | Per user |
| File uploads | 10 requests/min | Per user |

### 15.5 Audit Logging

All state-changing operations are logged:
- User creation, deletion, role changes
- Workspace membership changes
- Analysis job triggers and completions
- API key creation and revocation
- Failed authentication attempts

---

## 16. Scoring System

### 16.1 Production Readiness Score — Deep Dive

**5 Dimensions, 0-100 Each:**

```
                  ┌──────────────────────┐
                  │  PRODUCTION READINESS │
                  │       SCORE          │
                  │      (0-100)         │
                  └──────────┬───────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │Performance │  │  Security  │  │ Reliability│
    │  Score     │  │   Score    │  │   Score    │
    └────────────┘  └────────────┘  └────────────┘

    ┌────────────┐  ┌────────────┐
    │Maintain-   │  │  DevOps    │
    │ ability    │  │   Score    │
    │  Score     │  │            │
    └────────────┘  └────────────┘
```

**Scoring Algorithm:**

```python
def calculate_score(
    performance_score: float,
    security_score: float,
    reliability_score: float,
    maintainability_score: float,
    devops_score: float,
    simulation_status: str,  # "stable", "degraded", "failing"
) -> Score:

    # 1. Apply capacity penalties
    if simulation_status == "failing":
        performance_score -= 50
    elif simulation_status == "degraded":
        performance_score -= 20

    # 2. Clamp all scores to [0, 100]
    scores = [max(0, min(100, s)) for s in
              [performance_score, security_score,
               reliability_score, maintainability_score, devops_score]]

    # 3. Weighted average (equal weights)
    overall = sum(scores) / len(scores)

    # 4. Critical-Floor: If any category < 50, cap overall
    min_category = min(scores)
    if min_category < 50:
        overall = min(overall, min_category)

    # 5. Determine tier
    tier = classify_tier(overall)

    return Score(
        overall=overall,
        performance=performance_score,
        security=security_score,
        reliability=reliability_score,
        maintainability=maintainability_score,
        devops=devops_score,
        tier=tier
    )
```

**Penalty Calculation Per Finding:**

```python
SEVERITY_PENALTIES = {
    Severity.CRITICAL: 15,
    Severity.HIGH: 10,
    Severity.MEDIUM: 5,
    Severity.LOW: 2,
    Severity.INFO: 0,
}

# Log-normalized: more files = less penalty per finding
penalty = base_penalty * log(1 + count) / log(1 + total_files)
```

### 16.2 Score History & Trends

Score history is stored in TimescaleDB for time-series analysis:
- **Partitioning**: Daily chunks
- **Retention**: 1 year (configurable)
- **Aggregates**: Weekly and monthly averages pre-computed
- **Visualization**: Trend charts in workspace dashboard

---

## 17. Security Architecture

### 17.1 Defense in Depth

```
Layer 1: Network Security
├── Nginx reverse proxy (single entry point)
├── Rate limiting at proxy level
├── DDoS protection (AWS Shield)
└── VPC isolation (EKS in private subnets)

Layer 2: Transport Security
├── TLS 1.3 (HTTPS)
├── HSTS headers
├── Secure cookie flags (HTTPOnly, Secure, SameSite)
└── CSP headers

Layer 3: Authentication
├── JWT RS256 (asymmetric signing)
├── OAuth 2.0 (GitHub, Google, Apple)
├── MFA support
└── API key authentication

Layer 4: Authorization
├── RBAC (Owner, Admin, Member, Viewer)
├── Workspace isolation
├── API key scopes
└── Input validation (all endpoints)

Layer 5: Data Security
├── Encrypted OAuth tokens (AES-256)
├── Password hashing (bcrypt/Argon2)
├── Soft delete (audit trail)
├── SQL injection prevention (ORM)
└── Secret scanning (env files, code)

Layer 6: Monitoring
├── Sentry error tracking
├── Failed login detection
├── Anomaly detection
└── Audit logging
```

### 17.2 JWT Security

- **Algorithm**: RS256 (RSA Signature with SHA-256)
- **Key Generation**: 2048-bit RSA key pair
- **Signing**: Private key never exposed (server-side only)
- **Verification**: JWKS endpoint exposes public keys
- **Key Rotation**: Automatic key rotation via key IDs (kid)
- **Token Binding**: Access tokens tied to specific refresh tokens

### 17.3 Secret Management

- **Environment Variables**: `.env` files never committed (gitignored)
- **OAuth Tokens**: Encrypted at rest using AES-256-GCM
- **API Keys**: Stored as SHA-256 hashes (irreversible)
- **JWT Keys**: Volume-mounted `.keys/` directory (not in Docker image)
- **CI/CD**: GitHub Actions secrets for all API keys

---

## 18. Observability & Monitoring

### 18.1 Logging

| Service | Library | Format | Includes |
|---------|---------|--------|----------|
| Identity (Django) | structlog | JSON | correlation_id, user_id, request_id |
| Core (Django) | structlog | JSON | correlation_id, workspace_id, user_id |
| Analysis (FastAPI) | structlog | JSON | correlation_id, job_id, stage |
| AI (FastAPI) | structlog | JSON | correlation_id, model, tokens |

**Correlation ID Propagation:**
1. Client generates `X-Correlation-ID` header
2. Nginx passes header to all upstream services
3. Each service includes correlation_id in all log entries
4. Kafka messages include correlation_id for async event tracing

### 18.2 Metrics

**Prometheus Metrics Collected:**
- `http_requests_total` — Per-endpoint request counts
- `http_request_duration_seconds` — Request latency histograms
- `http_requests_in_flight` — Concurrent request count
- `analysis_jobs_total` — Analysis job counts by status
- `analysis_job_duration_seconds` — Job duration histograms
- `llm_calls_total` — LLM calls by provider and model
- `llm_duration_seconds` — LLM response time
- `llm_cost_total` — Cumulative LLM cost in USD
- `llm_tokens_total` — Token counts by type (input/output)

### 18.3 Error Tracking (Sentry)

**Captured Events:**
- Unhandled exceptions (500 errors)
- Configuration errors
- Database connection failures
- External service timeouts (LLM providers, GitHub API)
- Authentication failures
- Rate limit breaches

**Performance Monitoring:**
- API endpoint transaction traces
- Database query performance
- External HTTP call timing
- Celery task duration

---

## 19. Summary & Conclusion

### What Kraivor Is

Kraivor is a **unified developer intelligence platform** that combines code analysis, AI-powered insights, team collaboration, and production simulation into a single, integrated workspace. It serves individual developers, engineering teams, and enterprises with tiered offerings.

### What Makes It Revolutionary

1. **Production Simulation** — Kraivor doesn't just lint your code; it simulates how it will behave under production load at 100, 500, 5,000, and 50,000 concurrent users. This is a category-defining capability that no other code analysis tool offers.

2. **Multi-Dimensional Scoring** — The Production Readiness Score evaluates code across 5 orthogonal dimensions (Performance, Security, Reliability, Maintainability, DevOps) with a critical-floor mechanism that prevents teams from neglecting any dimension.

3. **AI-Native Multi-Agent System** — Built from the ground up with LangGraph, multi-provider LLM routing, and a RAG pipeline that understands your actual codebase. Not AI bolted onto an existing tool — AI is the architecture.

4. **Unified Workspace** — Eliminates the fragmented toolchain of GitHub + Jira + Notion + Slack + SonarQube by providing a single platform where code analysis, project management, knowledge management, team chat, and AI assistance converge.

5. **Enterprise-Grade from Day One** — Kubernetes manifests, Terraform modules, CI/CD pipelines, Postman collections, comprehensive monitoring (Sentry, Prometheus, OpenTelemetry), and security architecture (JWT RS256, OAuth 2.0, RBAC, encryption at rest).

### Technology Highlights

| Tool | Role in Kraivor |
|------|----------------|
| **LangChain** | Provider-agnostic LLM integration framework |
| **LangGraph** | Stateful multi-agent orchestration with conditional routing |
| **RAG** | Code-aware context retrieval for AI responses |
| **Celery** | Distributed async task processing |
| **Redis** | Caching, message broker, rate limiting, session store |
| **DynamoDB** | High-throughput chat history storage |
| **pgvector** | Vector similarity search in PostgreSQL (no separate DB needed) |
| **AWS S3** | Report and file artifact storage |
| **AWS Lambda** | Serverless notification dispatch |
| **GitHub App** | Deep repository integration and auto-syncing |
| **OAuth** | GitHub + Google identity federation |
| **WebSocket** | Real-time analysis progress and chat |
| **Sentry** | Production error tracking and performance monitoring |
| **Kafka** | Cross-service event-driven architecture |
| **TimescaleDB** | Time-series score history analytics |
| **Terraform** | Infrastructure-as-Code for AWS provisioning |
| **Kubernetes** | Production container orchestration |

### The Bottom Line

Kraivor is not just another developer tool. It is a **paradigm shift** from static code analysis to **production intelligence**. By simulating production conditions before deployment, providing AI-powered multi-dimensional insights, and unifying the developer toolchain into a single platform, Kraivor fundamentally changes how engineering teams understand and improve their code.

For individual developers, it's a personal co-pilot that catches issues before they reach production. For teams, it's a collaboration hub that connects code quality to project management. For enterprises, it's a governance platform that ensures production readiness across every repository.

**Kraivor: One platform. Three products. Production-grade from day one.**

---

*Documentation generated from Kraivor codebase v1.0.0*
*Last updated: June 2026*
