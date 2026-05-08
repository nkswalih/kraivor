# CI Migration Issues & Fixes

## Issue Summary

The auth service test suite failed on CI due to missing service dependencies.

## Problems Encountered

### 1. Model Registration Conflict
- **Error**: `RuntimeError: Model class apps.users.models.User doesn't declare an explicit app_label`
- **Cause**: App path naming mismatch between INSTALLED_APPS and Django registry
- **Fix**: Use simple names (`'users'`) not dotted names (`'apps.users'`)

### 2. Redis Not Available
- **Error**: `ConnectionRefusedError: Error 111 connecting to localhost:6379`
- **Cause**: Redis service not running in CI environment
- **Fix**: Add Redis service to CI workflow

### 3. SMTP Not Available
- **Error**: `ConnectionRefusedError: [Errno 111] Connection refused` (port 1025)
- **Cause**: MailHog not available in CI
- **Expected**: Tests should bypass email sending gracefully (logs errors but continues)

## Solutions Applied

### Fix 1: INSTALLED_APPS Configuration
```python
# Wrong (causes conflicts):
INSTALLED_APPS = ['apps.users', 'apps.authentication', 'apps.api_keys']

# Correct:
INSTALLED_APPS = ['users', 'authentication', 'api_keys']
```

### Fix 2: Add Redis to CI
```yaml
# .github/workflows/ci.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - 6379:6379
```

### Fix 3: AppConfig Labels
Each AppConfig needs correct name:
```python
# apps.py
class UsersConfig(AppConfig):
    name = 'users'  # NOT 'apps.users'
```

## Test Requirements

| Service | CI Status | Notes |
|---------|---------|-------|
| PostgreSQL | Required | Has healthcheck |
| Redis | Required | For lockout/OTP |
| SMTP | Optional | Logs errors but continues |

## Key Learnings

1. Django apps in subdirectories (`apps/users/`) must be registered with simple names in INSTALLED_APPS
2. All external services (Redis, Postgres) must be added to CI workflow `services:` block
3. Tests should handle service failures gracefully or mock appropriately