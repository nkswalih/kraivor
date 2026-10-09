# Contributing to Kraivor

First off, thank you for considering contributing to Kraivor. ❤️

Kraivor is an open-source developer intelligence platform focused on repository analysis, AI-powered engineering insights, developer productivity, and scalable software architecture. We welcome contributions of all sizes — from fixing a typo in the docs to building a new microservice.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Philosophy](#development-philosophy)
- [Project Architecture](#project-architecture)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Branching Strategy](#branching-strategy)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Security Guidelines](#security-guidelines)
- [Performance Considerations](#performance-considerations)
- [Documentation Contributions](#documentation-contributions)
- [Feature Requests](#feature-requests)
- [Community](#community)

---

## Code of Conduct

By participating, you agree to uphold the project's [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md). Be respectful, constructive, and collaborative — this is a community we're building together.

---

## Development Philosophy

Kraivor is built with a **production-grade engineering mindset**. Every contribution should reflect:

| Principle | Description |
|-----------|-------------|
| **Clean Architecture** | Separation of concerns, loosely coupled services, testable code |
| **Security First** | Least privilege, input validation, responsible disclosure |
| **Async & Event-Driven** | Non-blocking by default, background jobs for heavy work |
| **Developer Experience** | Clear APIs, helpful errors, great DX for contributors |
| **Maintainability** | Readable, consistent, well-documented code |
| **Performance** | Efficient queries, sensible caching, scalable design |
| **Open Collaboration** | Ideas welcome, feedback is a gift, ego stays at the door |

> **"Readability, consistency, performance, reliability — in that order."**

---

## Project Architecture

Kraivor follows a **service-oriented architecture**. Each service lives in `services/` and owns its data.

```
services/
├── auth/            # Django DRF — Authentication & User Management
├── core/            # Django DRF — Workspaces, Repos, Notes, Projects
├── analysis/        # FastAPI    — Repository Analyzer, Rule Engine, Scoring
└── ai/              # FastAPI    — Multi-Agent AI System, RAG Pipeline
```

### Primary Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django REST Framework, FastAPI |
| Database & Cache | PostgreSQL, Redis |
| Async Tasks & Events | Celery, Kafka |
| Frontend | Next.js, React 19, TypeScript, Tailwind CSS |
| Infrastructure | Docker, Kubernetes (EKS), Terraform, AWS |

---

## Getting Started

### 1. Fork the Repository

```bash
git clone https://github.com/your-username/kraivor.git
cd kraivor
```

### 2. Set Up Remotes

```bash
git remote add upstream https://github.com/your-org/kraivor.git
git fetch upstream
```

---

## Development Setup

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Node.js 18+
- Git

### Local Development

#### 1. Start Infrastructure

```bash
docker compose -f docker-compose.dev.yml up --build
```

#### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys and secrets.

#### 3. Install Dependencies

**Python service** (e.g., `services/ai`):

```bash
cd services/ai
uv sync --group dev
```

**Frontend**:

```bash
cd frontend
npm install
```

#### 4. Run Database Migrations

```bash
cd services/core
python manage.py migrate
```

---

## Branching Strategy

Create branches from `dev` and use descriptive names.

| Prefix | Example |
|--------|---------|
| `feat/` | `feat/workspace-member-management` |
| `fix/` | `fix/jwt-validation` |
| `refactor/` | `refactor/repository-service` |
| `docs/` | `docs/setup-guide` |
| `chore/` | `chore/update-dependencies` |

```bash
git checkout dev
git pull upstream dev
git checkout -b feat/your-feature-name
```

---

## Commit Guidelines

Write clear, descriptive commit messages following conventional commits:

```
<type>(<scope>): <description>
```

| Type | When to Use |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `refactor` | Code change that neither fixes nor adds |
| `docs` | Documentation only |
| `test` | Adding or fixing tests |
| `chore` | Tooling, dependencies, CI |
| `perf` | Performance improvement |
| `ci` | CI/CD configuration |

**Examples:**

```
feat(core): add workspace invitation flow
fix(auth): resolve JWT refresh validation issue
refactor(analysis): simplify repository scanner pipeline
docs(readme): update Docker setup instructions
```

---

## Pull Request Process

### Before Opening a PR

`make check` runs the hard CI gates in the order CI runs them:

```bash
make check          # lint + tests + security + frontend
```

Individually:

- [ ] `make lint` passes (ruff, all four services) — **required**
- [ ] `make test` passes and clears each service's coverage floor — **required**
- [ ] `make security` passes (bandit + pip-audit) — **required**
- [ ] `make frontend-check` passes (tsc, vitest, production build) — **required**
- [ ] `make format` and `make typecheck` are clean — advisory, same as CI
- [ ] Pre-commit hooks pass (`make precommit`)
- [ ] Rebased on latest `dev` branch
- [ ] PR is focused on a single concern (small PRs review faster)
- [ ] Description is clear and thorough

Two things worth knowing, because they used to hide failures:

- **`make test` and `make lint` fail on failure.** They used to end every
  command with `|| true`, so they exited 0 unconditionally and a broken suite
  looked identical to a green one. They also ran `manage.py test` for the
  Django services where CI runs `pytest`, which is a different test runner
  against pytest-style suites — and it cannot produce the coverage report.
  `make test` now runs `pytest --cov`, so the `fail_under` floor in each
  service's `pyproject.toml` is enforced locally too.
- **The frontend has no `services/` directory.** Its gates are the
  `package.json` scripts: `npm run typecheck`, `npm test`, `npm run build`.
  There is no separate lint target because `next build` runs ESLint as a
  gate; `typecheck` and `vitest` both pass with lint errors present.

### Coverage Floors

Each service holds itself to its own number in its own `pyproject.toml`, under
`[tool.coverage.report] fail_under`:

| Service | Floor |
|---------|-------|
| `auth` | 88% |
| `core` | 55% |
| `analysis` | 64% |
| `ai` | 27% |

The floors are uneven on purpose. `ai` is a thin orchestration layer over
provider SDKs and has little of its own to cover; `auth` holds credential and
token logic where a missed branch is a security bug. Dropping a floor to make a
red build green is not a fix — add the test.

### PR Template

```markdown
## Summary
<!-- Brief description of changes -->

## Related Issues
<!-- Closes #123, Fixes #456 -->

## Screenshots (if UI change)
<!-- Add screenshots here -->

## Migration Notes (if applicable)
<!-- Any DB migrations, env changes, etc. -->

## Checklist
- [ ] Tests added/updated
- [ ] Lint passes
- [ ] Docs updated (if needed)
```

---

## Coding Standards

### Python

- Follow **PEP 8**
- Use **type hints** wherever possible
- Keep functions small and focused (single responsibility)
- Prefer explicit over implicit
- Avoid unnecessary abstractions

**Pre-commit Hooks (run before every commit):**

```bash
make precommit
```

Or manually:

```bash
ruff check .
ruff format .
isort --check-only --diff .
black --check --diff .
mypy .
bandit -r . -x ./tests
```

### Backend (Django DRF / FastAPI)

- Keep views thin — business logic belongs in **service layer**
- Use serializers / Pydantic for **input validation**
- Use **transactions** for multi-step database operations
- **Avoid N+1 queries** — use `select_related` / `prefetch_related`
- Offload heavy work to **background tasks** (Celery / Kafka)

### Frontend (Next.js / React / TypeScript)

- Use **TypeScript** — strict mode enabled
- Prefer **server components** where appropriate (Next.js App Router)
- Keep components **modular and composable**
- Use **Tailwind CSS** for styling — avoid CSS-in-JS for new components
- Use **Zustand** for global state, **TanStack Query** for server state
- Avoid **deeply nested state** — flatten where possible
- Run lint and typecheck before committing:

```bash
npm run lint
npm run typecheck
```

---

## Testing Requirements

All significant changes **must include tests**.

### Coverage Focus

- API behavior (status codes, response shape)
- Permissions and authorization
- Business logic and edge cases
- Security-sensitive flows
- Error handling paths

### Running Tests

```bash
# All services, with coverage gates -- what CI runs
make test

# Everything CI treats as a hard gate
make check

# Individual service (using uv)
cd services/analysis && uv run pytest tests/ -v

# Frontend
cd frontend && npm test
```

### JWT Keys for the Auth Service

`auth`'s test suite signs real JWTs and needs an RSA keypair on disk. CI
generates it in `services/auth/.keys/`, which is gitignored, so a fresh clone
will fail the auth suite until you create it once:

```bash
mkdir -p services/auth/.keys && cd services/auth/.keys
openssl genrsa -out jwt-private.pem 2048
openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem
```

This never bit anyone before because `make test` ended in `|| true` and the
auth service ran under `manage.py test` instead of `pytest`, so neither the
missing keys nor a genuine failure could stop the run. Now that the gate is
real, the missing keys surface as a genuine failure.

---

## Security Guidelines

Security is a **core priority** at Kraivor.

### Responsible Disclosure

- **Do NOT** create public GitHub issues for vulnerabilities
- Email maintainers privately with:
  - Clear description of the issue
  - Reproduction steps
  - Affected versions
- Allow time for remediation before public disclosure

### Secure Coding Practices

- Validate and sanitize all user input
- Use parameterized queries — never raw SQL interpolation
- Apply least privilege to API keys and service accounts
- Never commit secrets, tokens, or credentials to the repository

---

## Performance Considerations

When contributing, keep these principles in mind:

- **Avoid blocking operations** — use async patterns for I/O
- **Optimize database queries** — measure, then optimize
- **Cache aggressively** — Redis is your friend
- **Avoid excessive memory usage** — paginate large datasets
- **Design for scale** — consider how your change behaves at 100x the load
- **Large repo analysis** must remain efficient, fault-tolerant, and observable

---

## Documentation Contributions

Documentation improvements are **highly valued** and are some of the most impactful contributions you can make.

Great places to start:

- Fixing typos or unclear instructions in the README or docs
- Adding architecture diagrams
- Writing API usage examples
- Improving developer onboarding guides
- Translating documentation

---

## Feature Requests

Have an idea? We'd love to hear it. Open a [GitHub Discussion](https://github.com/your-org/kraivor/discussions) and include:

- **Problem statement** — what are you trying to solve?
- **Proposed solution** — how should it work?
- **Use cases** — who benefits and how?
- **Expected impact** — does this unblock teams, improve DX, etc.?

---

## Community

Kraivor is more than a project — it's a community. Join us:

- **Discord** — real-time chat, help, and collaboration
- **GitHub Discussions** — feature ideas, Q&A, show and tell
- **X / Twitter** — follow for updates and community highlights

We aim to build a **welcoming, technically strong, and inclusive** open-source community. Constructive collaboration and respectful communication are expected from everyone.

Thank you for helping make Kraivor better — one commit at a time. 🚀
