# Kraivor

One platform. Three products. Production-grade from day one.

Kraivor is a unified developer intelligence platform built as a microservices system. It combines a Repository Analyzer, Agentic AI System, and Developer Productivity Platform into a single authenticated workspace.

## Project Structure

```
kraivor/
├── services/           # Microservices (6 services)
│   ├── identity/       # Django DRF - Authentication & User Management
│   ├── core/           # Django DRF - Workspaces, Repos, Notes, Projects
│   ├── analysis/       # FastAPI - Repository Analyzer
│   ├── ai/             # FastAPI - Multi-Agent AI System
│   ├── notifications/  # FastAPI - Email, Push, Slack notifications
│   └── realtime/       # Node.js - WebSocket & Real-time updates
├── frontend/          # Next.js web application
├── infra/             # Infrastructure as Code
│   ├── docker/         # Nginx, Postgres configs
│   ├── kubernetes/     # K8s manifests
│   └── terraform/      # AWS infrastructure
└── .github/           # CI/CD workflows
```

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Kafka (or use Docker)

## Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/kraivor.git
   cd kraivor
   ```

2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your API keys and secrets.

3. Start all services:
   ```bash
   make dev
   ```

4. Run tests:
   ```bash
   make test
   ```

5. View logs:
   ```bash
   make logs
   ```

6. Stop all services:
   ```bash
   make stop
   ```

## Services

| Service | Port | Framework | Description |
|---------|------|-----------|-------------|
| Identity | 8001 | Django DRF | Auth, Users, API Keys, OAuth |
| Core API | 8002 | Django DRF | Workspaces, Repos, Notes, Projects |
| Analysis | 8003 | FastAPI | Repo Analyzer, Rule Engine, Scoring |
| AI | 8004 | FastAPI | Multi-Agent AI, RAG Pipeline |
| Notifications | 8005 | FastAPI | Email, Push, Slack notifications |
| Realtime | 8006 | Node.js | WebSocket, Chat, Presence |

## Key Features

### Repository Analyzer
Deep structural analysis of codebases with Production Readiness Scores and prioritized reports.

### Agentic AI System
Multi-agent AI workspace with specialized agents for code analysis, architecture review, security, and performance.

### Developer Productivity Platform
Unified workspace for notes, projects, and tasks with AI-enhanced context.

## Architecture Principles

- **Single entry point** through API Gateway (Nginx + Kong)
- **Async by default** - operations >500ms run as background jobs
- **Service owns its data** - no cross-service database queries
- **Fail gracefully** - services degrade independently
- **Everything observable** - correlation IDs, structured logs, metrics

## Deployment

- **Staging**: Auto-deployed from `dev` branch
- **Production**: Auto-deployed from `main` branch
- **Infrastructure**: AWS EKS, RDS, ElastiCache, S3, Kafka (MSK)

## Contributing

1. Create a feature branch from `dev`
2. Make your changes
3. Run `make test` to ensure all tests pass
4. Submit a pull request to `dev`

## License

[Add your license here]
