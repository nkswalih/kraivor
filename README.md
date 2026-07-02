## 🐍 Kraivor — developer intelligence OS

<div align="center">

  <picture>
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/nkswalih/kraivor/dev/docs/assets/kraivor_text_logo.svg">
    <img src="https://raw.githubusercontent.com/nkswalih/kraivor/dev/docs/assets/kraivor_text_logo.svg" alt="Kraivor" width="500">
  </picture>

  <p><strong>One workspace. Infinite codebase memory.</strong></p>

  <br>

  <!-- Badges -->
  <p>
    <a href="https://github.com/nkswalih/kraivor/actions"><img src="https://img.shields.io/github/actions/workflow/status/nkswalih/kraivor/ci.yml?style=flat-square&logo=github&label=build" alt="Build Status"></a>
    <a href="https://github.com/nkswalih/kraivor/blob/dev/LICENSE"><img src="https://img.shields.io/github/license/nkswalih/kraivor?style=flat-square&color=blue" alt="License"></a>
    <!-- <a href="https://github.com/nkswalih/kraivor/releases"><img src="https://img.shields.io/github/v/release/nkswalih/kraivor?style=flat-square&logo=semver" alt="Version"></a> -->
    <a href="https://github.com/nkswalih/kraivor/stargazers"><img src="https://img.shields.io/github/stars/nkswalih/kraivor?style=flat-square&logo=github" alt="Stars"></a>
    <a href="https://github.com/nkswalih/kraivor/graphs/contributors"><img src="https://img.shields.io/github/contributors/nkswalih/kraivor?style=flat-square&logo=contributorcovenant" alt="Contributors"></a>
    <a href="https://github.com/nkswalih/kraivor/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square&logo=github" alt="PRs Welcome"></a>
    <a href="https://discord.gg/rgdV8Uh6D"><img src="https://img.shields.io/badge/chat-discord-5865F2?style=flat-square&logo=discord" alt="Discord"></a>
  </p>
  
  <p>Kraivor is a unified developer intelligence platform that combines a <strong>Repository Analyzer</strong>, <strong>Agentic AI System</strong>, and <strong>Developer Productivity Platform</strong> into a single authenticated workspace — giving engineering teams deep code insights, AI-powered assistance, and a collaborative hub, all out of the box.</p>
</div>

---

## About the Project

Engineering teams today juggle too many tools — repository analysis, AI coding assistants, project management, documentation — all scattered across different platforms with no shared context. Kraivor solves this by bringing everything into **one unified workspace**.

What makes Kraivor different:

- **Deep, structural code analysis** — not just linting, but a full Production Readiness Score with prioritized, actionable reports.
- **Multi-agent AI** — specialized agents for architecture review, security auditing, performance profiling, and code generation that share context and collaborate.
- **Built for scale from day one** — async-first microservices, event-driven architecture, and full observability out of the box. No "we'll fix it in production."

Whether you're a solo developer looking to level up your code quality or a platform team standardizing engineering practices across 100+ repos, Kraivor gives you the intelligence layer your workflow has been missing.

---

## Features

| Area | Description |
|------|-------------|
| **Repository Analyzer** | Deep structural analysis of any codebase. Generates actionable Production Readiness Scores with prioritized remediation reports across security, performance, maintainability, and architecture. |
| **Agentic AI System** | A multi-agent AI workspace where specialized agents (architecture, security, performance, code gen) collaborate on your codebase with full context awareness and a RAG pipeline. |
| **Developer Productivity Platform** | Unified workspace for notes, projects, and tasks — enhanced with AI context from your repositories. Drag-and-drop project boards, real-time collaboration, and rich markdown editing. |
| **Real-Time Collaboration** | WebSocket-powered live updates, chat, presence indicators, and collaborative editing so your team stays in sync without leaving the platform. |
| **Production-Grade Infrastructure** | Async-first design, event-driven communication via Kafka, full observability with correlation IDs and structured logging, and graceful degradation across all services. |

---

## Architecture & Tech Stack

Kraivor follows a **service-oriented architecture** with a single API Gateway (Nginx + Kong) as the entry point. Each service owns its data, communicates asynchronously via Kafka, and is independently deployable.

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────────┐
│  Frontend   │────▶│  API Gateway  │────▶│   Microservices      │
│  (Next.js)  │     │  Nginx/Kong   │     │  Django DRF/FastAPI  │
└─────────────┘     └──────────────┘     └──────────────────────┘
                          │                        │
                          ▼                        ▼
                   ┌──────────────┐     ┌──────────────────────┐
                   │   WebSocket  │     │   Kafka / Celery     │
                   │   (Node.js)  │     │   (Async Tasks)      │
                   └──────────────┘     └──────────────────────┘
                                                │
                                                ▼
                                        ┌──────────────────┐
                                        │  PostgreSQL/Redis │
                                        │  (Data & Cache)   │
                                        └──────────────────┘
```

**Primary Stack:**

| Layer | Technology |
|-------|-----------|
| **Backend** | Django REST Framework, FastAPI, Node.js |
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS |
| **Database & Cache** | PostgreSQL, Redis |
| **Async & Events** | Celery, Kafka (MSK) |
| **Infrastructure** | Docker, Kubernetes (EKS), Terraform, AWS |
| **Observability** | Structured logging, Correlation IDs, Metrics |

---

## Services Overview

| Service | Port | Framework | Description |
|---------|------|-----------|-------------|
| Identity | `8001` | Django DRF | Auth, Users, API Keys, OAuth |
| Core API | `8002` | Django DRF | Workspaces, Repos, Notes, Projects |
| Analysis | `8003` | FastAPI | Repo Analyzer, Rule Engine, Scoring |
| AI | `8004` | FastAPI | Multi-Agent AI, RAG Pipeline |
| Notifications | `8005` | FastAPI | Email, Push, Slack notifications |
| Realtime | `8006` | Node.js | WebSocket, Chat, Presence |

**Architecture Principles:**

- **Single entry point** through API Gateway (Nginx + Kong)
- **Async by default** — operations >500ms run as background jobs
- **Service owns its data** — no cross-service database queries
- **Fail gracefully** — services degrade independently
- **Everything observable** — correlation IDs, structured logs, metrics

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Kafka (or use Docker)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/your-org/kraivor.git
cd kraivor

# 2. Copy environment variables
cp .env.example .env
# Edit .env and fill in your API keys and secrets

# 3. Start all services (uses docker-compose)
make dev
```

### Quick Start

Once the services are running, navigate to `http://localhost:3000` and create your account. From there:

1. **Create a workspace** — your team's collaborative hub
2. **Connect a repository** — paste a GitHub/GitLab URL and run analysis
3. **Explore AI insights** — ask architecture questions, review security findings, get performance recommendations

<details>
<summary><b>Useful Makefile Commands</b></summary>

```bash
make dev    # Start all services
make stop   # Stop all services
make logs   # View logs from all services
make test   # Run tests for all services
```

</details>

---

## Documentation & Roadmap

Full documentation is available at **[docs.kraivor.dev](https://docs.kraivor.dev)** (coming soon). In the meantime, check the `docs/` directory in this repository for API references and architecture guides.

### Roadmap

- **Q3 2026** — VSCode & JetBrains IDE extensions, custom rule engine for analysis, GitHub Actions integration
- **Q4 2026** — Self-hosted deployment mode, SSO/SAML support, advanced RAG with local LLM support
- **Q1 2027** — API-first marketplace for community plugins, on-premise Kubernetes operator, SOC 2 compliance

---

## Contributing

We ❤️ contributions of all sizes — from fixing a typo to building a new service.

1. Fork the repo and create a feature branch from `dev`
2. Make your changes (and add tests where appropriate)
3. Run `make test` to ensure everything passes
4. Submit a pull request to `dev`

Check out [`CONTRIBUTING.md`](./CONTRIBUTING.md) for detailed guidelines, and our [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) for community standards.

<a href="https://github.com/nkswalih/kraivor/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=nkswalih/kraivor" alt="Contributors Graph" />
</a>

---

## Community & Support

- **💬 Discord** — [Join our server](https://discord.gg/rgdV8Uh6D) for real-time chat
- **🐙 GitHub Discussions** — Ask questions, share ideas, and show off what you build
<!-- - **🐦 X / Twitter** — Follow [@kraivor](https://twitter.com/kraivor) for updates -->
<!-- - **📧 Email** — [hello@kraivor.dev](mailto:hello@kraivor.dev) for business inquiries -->

---

## License

Distributed under the **MIT License**. See [`LICENSE`](./LICENSE) for more information.

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/nkswalih">Mohammed Swalih N K</a> and the Kraivor community.</sub>
</p>
