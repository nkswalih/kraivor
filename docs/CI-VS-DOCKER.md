# CI vs Docker Development

## Overview

This document explains why local Docker and GitHub Actions CI behave differently.

## Local Development (Docker)

When you run `docker-compose up`:
- All services start together (postgres, redis, mailhog, identity, etc.)
- Services communicate via Docker network
- Tests can use real Redis/PostgreSQL

```bash
# Start all services locally
docker-compose up

# Run tests in Docker
docker-compose exec identity uv run python manage.py test
```

## CI (GitHub Actions)

GitHub Actions runs on **bare virtual machines**, not Docker containers:
- Only services defined in `services:` block are available
- No Docker daemon access
- Each job is isolated

### CI Services Block
```yaml
# .github/workflows/ci.yml
jobs:
  test-identity:
    services:
      postgres:
        image: postgres:15
        # ... healthcheck config
      redis:
        image: redis:7-alpine
        # ... healthcheck config
```

What's NOT available in CI:
- ❌ MailHog (need to add or skip email tests)
- ❌ Kafka
- ❌ Other docker-compose services

## Why Tests Fail on CI but Work Locally

| Service | Docker Compose | CI | Notes |
|---------|--------------|---|-------|
| PostgreSQL | ✅ | ✅ | In both |
| Redis | ✅ | ✅ | Now added |
| MailHog | ✅ | ❌ | Logs errors |
| Kafka | ✅ | ❌ | Not used in auth |

## Solutions

### Option 1: Add Services to CI
Add more services to CI workflow if needed:
```yaml
services:
  mailhog:
    image: mailhog/mailhog:latest
    ports:
      - 1025:1025
```

### Option 2: Mock External Services
Use `@patch` to mock services:
```python
@patch('users.email_service.email_service')
def test_signup(self, mock_email):
    mock_email.send_verification_email = lambda u, t: None
```

### Option 3: Conditional Tests
```python
import os
SKIP_EMAIL_TESTS = os.environ.get('CI', False)
```

## Best Practice

For auth service tests:
1. Redis required → Add to CI services ✅ (Done)
2. PostgreSQL required → Add to CI services ✅
3. Email optional → Already handles gracefully (logs errors, continues)

## Running Tests Locally vs CI

```bash
# Local (Docker)
docker-compose up -d postgres redis mailhog
docker-compose exec identity uv run python manage.py test

# CI (GitHub Actions)
# Services defined in workflow (postgres + redis)
uv run python manage.py test
```

## Key Takeaway

**CI ≠ Docker** - They are different environments. Always verify your CI workflow has all required services defined.