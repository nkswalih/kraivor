# Contributing to Kraivor

First off, thank you for considering contributing to Kraivor.

Kraivor is an open-source developer intelligence platform focused on repository analysis, AI-powered engineering insights, developer productivity, and scalable software architecture.

We welcome contributions of all sizes — from bug fixes and documentation improvements to large architectural enhancements.

---

# Table of Contents

- Code of Conduct
- Development Philosophy
- Project Architecture
- Getting Started
- Development Setup
- Branching Strategy
- Commit Guidelines
- Pull Request Process
- Coding Standards
- Testing Requirements
- Security Guidelines
- Issue Reporting
- Feature Requests
- Community

---

# Code of Conduct

By participating in this project, you agree to follow the project's `CODE_OF_CONDUCT.md`.

Please be respectful, constructive, and collaborative.

---

# Development Philosophy

Kraivor is built with a production-grade engineering mindset.

Core principles:

- Clean architecture
- Scalable backend systems
- Security-first development
- Async and event-driven design
- Developer experience
- Maintainable codebases
- Open collaboration

We prioritize:
- readability
- consistency
- performance
- reliability

over unnecessary complexity.

---

# Project Architecture

Kraivor follows a service-oriented architecture.

Current services include:

```text
services/
├── auth/
├── core/
├── analysis/
├── ai/
├── notifications/
└── realtime/

# Kraivor Project Documentation

## Primary Stack
* **Backend:** Django DRF, FastAPI
* **Database & Caching:** PostgreSQL, Redis
* **Message Brokers & Task Queues:** Celery, Kafka
* **DevOps & Containerization:** Docker
* **Frontend:** Next.js

---

## Getting Started

### 1. Fork the Repository
Fork the repository and clone your fork locally.
```bash
git clone https://github.com/your-username/kraivor.git
cd kraivor
```

---

## Development Setup

### Requirements
* Python 3.11+
* Docker & Docker Compose
* PostgreSQL
* Redis
* Git

### Local Setup

#### 1. Start development infrastructure
```bash
docker compose -f docker-compose.dev.yml up --build
```

#### 2. Create environment variables
```bash
cp .env.example .env
```
*Note: Update values as needed.*

#### 3. Install dependencies
Example for core service:
```bash
cd services/core
uv venv
uv sync --all-groups
```

#### 4. Run tests
```bash
uv run pytest
```

---

## Branching Strategy
Use descriptive branch names.

**Examples:**
* `feat/workspace-member-management`
* `fix/jwt-validation`
* `refactor/repository-service`
* `docs/setup-guide`

---

## Commit Guidelines
Use clear and descriptive commit messages.

**Examples:**
* `feat(core): add workspace invitation flow`
* `fix(auth): resolve JWT refresh validation issue`
* `refactor(analysis): simplify repository scanner pipeline`
* `docs(readme): update Docker setup instructions`

**Recommended commit types:**
* `feat` / `fix` / `refactor`
* `docs` / `test` / `chore`
* `perf` / `ci`

---

## Pull Request Process
Before opening a PR, ensure you:
* Ensure tests pass
* Ensure lint checks pass
* Rebase on latest main branch
* Keep PRs focused and small
* Add clear descriptions

**PRs should include:**
* Summary of changes
* Screenshots if UI changes
* Related issue/ticket references
* Migration notes if applicable

---

## Coding Standards

### Python
* Follow PEP8
* Use type hints where possible
* Keep functions focused
* Avoid unnecessary abstractions
* Prefer explicit over implicit behavior

**Formatting and linting:**
```bash
ruff check .
ruff format .
```

### Backend Standards
* Keep views thin
* Put business logic in services
* Use serializers for validation
* Use transactions where required
* Avoid N+1 queries
* Use async workflows for heavy tasks

### Frontend Standards
* Use TypeScript
* Prefer server components when appropriate
* Keep components modular
* Avoid deeply nested state

---

## Testing Requirements
All significant changes should include tests.

**Recommended test coverage:**
* API behavior
* Permissions
* Business logic
* Edge cases
* Security-sensitive flows

**Run tests:**
```bash
pytest
```

---

## Security Guidelines
Security is a core priority. Please follow responsible disclosure practices.

### Reporting Security Issues
* Do **NOT** create public GitHub issues for vulnerabilities.
* Contact maintainers privately.
* Provide reproduction details.
* Allow time for remediation.

---

## Performance Considerations
When contributing, please:
* Avoid blocking operations
* Optimize database queries
* Avoid excessive memory usage
* Consider scalability impacts
* Ensure large repository analysis remains efficient and fault-tolerant.

---

## Documentation Contributions
Documentation improvements are highly appreciated.

**Examples:**
* Setup guides
* Architecture explanations
* Diagrams
* API documentation
* Developer onboarding

---

## Feature Requests
Feature requests are welcome. Please include:
* Problem statement
* Proposed solution
* Use cases
* Expected impact

---

## Community
We aim to build a welcoming and technically strong open-source community. Constructive collaboration and respectful communication are expected from all contributors.

Thank you for contributing to Kraivor.
