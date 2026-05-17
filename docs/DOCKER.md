# Kraivor — Docker Command Reference

Everything you need to run, debug, and manage the Kraivor stack locally and in production.

---

## Quick Start

### First time ever
```bash
# 1. Copy the example env file and fill in your values
cp .env.example .env

# 2. Auth dev only (recommended for daily auth work)
docker-compose -f docker-compose.dev.yml up --build

# 3. Full stack
docker-compose up --build
```

### Every day after that
```bash
# Auth dev only
docker-compose -f docker-compose.dev.yml up

# Full stack
docker-compose up
```

---

## Dev Stack (Auth Only)

Use this when working on the identity/auth service. Starts: postgres, redis, mailhog, identity.

```bash
# Start (build image if it doesn't exist)
docker-compose -f docker-compose.dev.yml up

# Start and force rebuild the image
docker-compose -f docker-compose.dev.yml up --build

# Start in background (detached)
docker-compose -f docker-compose.dev.yml up -d

# Start and rebuild in background
docker-compose -f docker-compose.dev.yml up --build -d

# Stop (keeps containers and volumes)
docker-compose -f docker-compose.dev.yml stop

# Stop and remove containers (keeps volumes — your DB data is safe)
docker-compose -f docker-compose.dev.yml down

# Nuclear — stop, remove containers AND delete all volumes (wipes DB)
docker-compose -f docker-compose.dev.yml down -v
```

---

## Full Stack

Starts all services: postgres, redis, kafka, identity, core, analysis, ai, notifications, realtime, frontend, nginx.

```bash
# Start everything
docker-compose up

# Start and rebuild all images
docker-compose up --build

# Start in background
docker-compose up -d

# Start only specific services
docker-compose up postgres redis identity

# Start full stack + mailhog (dev profile)
docker-compose --profile dev up

# Stop everything (keeps volumes)
docker-compose down

# Stop and wipe all volumes
docker-compose down -v

# Rebuild one service without touching the rest
docker-compose up --build identity
```

---

## Logs

```bash
# All services, follow live
docker-compose -f docker-compose.dev.yml logs -f

# One service, follow live
docker-compose -f docker-compose.dev.yml logs -f identity

# Last 100 lines from one service
docker-compose -f docker-compose.dev.yml logs --tail=100 identity

# Multiple services at once
docker-compose -f docker-compose.dev.yml logs -f identity postgres

# Full stack logs
docker-compose logs -f

# Full stack, one service
docker-compose logs -f core
```

---

## Running Commands Inside Containers

```bash
# Open a bash shell inside the running identity container
docker-compose -f docker-compose.dev.yml exec identity bash

# Run a one-off Django management command
docker-compose -f docker-compose.dev.yml exec identity python manage.py migrate
docker-compose -f docker-compose.dev.yml exec identity python manage.py createsuperuser
docker-compose -f docker-compose.dev.yml exec identity python manage.py shell
docker-compose -f docker-compose.dev.yml exec identity python manage.py showmigrations

# Run tests inside the container
docker-compose -f docker-compose.dev.yml exec identity pytest
docker-compose -f docker-compose.dev.yml exec identity pytest tests/test_krv014_sessions.py -v
docker-compose -f docker-compose.dev.yml exec identity pytest --tb=short

# Check installed packages
docker-compose -f docker-compose.dev.yml exec identity pip list

# Connect to postgres directly
docker-compose -f docker-compose.dev.yml exec postgres psql -U kraivor -d kraivor

# Run a postgres query inline
docker-compose -f docker-compose.dev.yml exec postgres psql -U kraivor -d kraivor -c "SELECT * FROM auth_refresh_tokens LIMIT 10;"

# Flush redis
docker-compose -f docker-compose.dev.yml exec redis redis-cli FLUSHALL
```

---

## Migrations

```bash
# Run all pending migrations
docker-compose -f docker-compose.dev.yml exec identity python manage.py migrate

# Make new migrations after model changes
docker-compose -f docker-compose.dev.yml exec identity python manage.py makemigrations

# Make migrations for a specific app
docker-compose -f docker-compose.dev.yml exec identity python manage.py makemigrations authentication

# Show migration status
docker-compose -f docker-compose.dev.yml exec identity python manage.py showmigrations

# Show migration SQL without running it
docker-compose -f docker-compose.dev.yml exec identity python manage.py sqlmigrate authentication 0001

# Roll back to a specific migration
docker-compose -f docker-compose.dev.yml exec identity python manage.py migrate authentication 0002
```

---

## Building Images

```bash
# Build dev image
docker-compose -f docker-compose.dev.yml build identity

# Build prod image
docker-compose build identity

# Build with no cache (full clean rebuild — use when dependencies change)
docker-compose -f docker-compose.dev.yml build --no-cache identity
docker-compose build --no-cache identity

# Build all prod services
docker-compose build

# Build and push to registry (prod deployment)
docker-compose build identity
docker tag kraivor-identity your-registry.com/kraivor/identity:latest
docker push your-registry.com/kraivor/identity:latest
```

---

## Container Status & Inspection

```bash
# See all running containers and their status
docker-compose -f docker-compose.dev.yml ps
docker-compose ps

# See resource usage (CPU, memory, network) live
docker stats

# Stats for just the kraivor containers
docker stats kraivor-identity-dev kraivor-postgres-dev kraivor-redis-dev

# Inspect a container (full config, IP, mounts, env vars)
docker inspect kraivor-identity-dev

# See what ports are mapped
docker-compose -f docker-compose.dev.yml port identity 8001

# List all volumes
docker volume ls

# Inspect a volume (see where data is on disk)
docker volume inspect kraivor_postgres_data_dev
```

---

## Cleanup

```bash
# Remove stopped containers
docker container prune

# Remove unused images (keeps tagged ones)
docker image prune

# Remove ALL unused images including tagged (dangerous — rebuilds from scratch)
docker image prune -a

# Remove unused volumes (dangerous — data loss)
docker volume prune

# Remove unused networks
docker network prune

# Full nuclear cleanup — removes everything Docker-related not currently running
# WARNING: removes all images, containers, volumes, networks
docker system prune -a --volumes

# See how much disk Docker is using
docker system df
```

---

## Troubleshooting

### Container won't start

```bash
# Check what happened
docker-compose -f docker-compose.dev.yml logs identity

# Check the last exit code
docker-compose -f docker-compose.dev.yml ps

# Run the container interactively to debug startup
docker-compose -f docker-compose.dev.yml run --rm identity bash
```

### Dependency / import errors after pulling changes

```bash
# pyproject.toml changed — rebuild the image to re-run uv sync
docker-compose -f docker-compose.dev.yml up --build identity
```

### Port already in use

```bash
# Find what is using port 8001
lsof -i :8001          # macOS / Linux
netstat -ano | findstr :8001   # Windows

# Kill it
kill -9 <PID>
```

### Database connection refused

```bash
# Check postgres is healthy
docker-compose -f docker-compose.dev.yml ps postgres

# Check postgres logs
docker-compose -f docker-compose.dev.yml logs postgres

# Restart just postgres
docker-compose -f docker-compose.dev.yml restart postgres
```

### Migrations out of sync / broken state

```bash
# Check current state
docker-compose -f docker-compose.dev.yml exec identity python manage.py showmigrations

# If totally broken, wipe the dev DB and start fresh
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up --build
```

### venv / package not found errors

```bash
# The venv lives at /opt/venv inside the image (not /app).
# If you see ModuleNotFoundError, rebuild the image — never mount a volume over /opt/venv.
docker-compose -f docker-compose.dev.yml build --no-cache identity
docker-compose -f docker-compose.dev.yml up identity
```

### Check emails sent in dev

Open **http://localhost:8025** — MailHog catches all outgoing email.

---

## Service URLs (Dev)

| Service       | URL                          | Notes                        |
|---------------|------------------------------|------------------------------|
| Auth API      | http://localhost:8001/api/   | Identity service             |
| Core API      | http://localhost:8002/api/   | Full stack only              |
| Analysis API  | http://localhost:8003/api/   | Full stack only              |
| AI API        | http://localhost:8004/api/   | Full stack only              |
| Notifications | http://localhost:8005/api/   | Full stack only              |
| Realtime WS   | ws://localhost:8006          | Full stack only              |
| Frontend      | http://localhost:3000        | Full stack only              |
| Nginx         | http://localhost:80          | Full stack only              |
| MailHog UI    | http://localhost:8025        | Dev email catcher            |
| PostgreSQL    | localhost:5433               | User: kraivor / PW from .env |
| Redis         | localhost:6379               | No auth in dev               |

---

## Common Workflows

### Start fresh for the day
```bash
docker-compose -f docker-compose.dev.yml up
```

### After pulling new code with model changes
```bash
docker-compose -f docker-compose.dev.yml up --build
docker-compose -f docker-compose.dev.yml exec identity python manage.py migrate
```

### Run a specific test file
```bash
docker-compose -f docker-compose.dev.yml exec identity pytest tests/test_krv014_sessions.py -v
```

### Completely wipe dev environment and start clean
```bash
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up --build
```

### Check auth token in the database
```bash
docker-compose -f docker-compose.dev.yml exec postgres \
  psql -U kraivor -d kraivor -c \
  "SELECT id, device_name, device_type, revoked, expires_at FROM auth_refresh_tokens ORDER BY created_at DESC LIMIT 5;"
```
