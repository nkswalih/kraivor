# =============================================================================
# Dockerfile — Core Service (Production)
# =============================================================================
# Multi-stage build:
#   Stage 1 (builder) — install deps into an isolated venv via uv
#   Stage 2 (runtime) — copy only the venv + app code, no build tools
# =============================================================================

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# System deps needed only at build time
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (pinned version for reproducible builds)
COPY --from=ghcr.io/astral-sh/uv:0.4.30 /uv /usr/local/bin/uv

# uv settings
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PYTHONDONTWRITEBYTECODE=1

# Copy dependency manifest first — Docker cache layer
COPY pyproject.toml uv.lock /app/

# Install production deps only into /app/.venv
RUN uv sync --frozen --no-dev

# Copy application source
COPY . /app/

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system deps only (libpq for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy venv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY --from=builder /app /app

# Put venv on PATH — no `source activate` needed
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Collect static files at build time
RUN SECRET_KEY=build-time-placeholder \
    DATABASE_URL=sqlite:///dev-null \
    python manage.py collectstatic --noinput --clear 2>/dev/null || true

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8002

CMD ["sh", "-c", \
     "uvicorn core.asgi:application \
      --host 0.0.0.0 \
      --port 8002 \
      --workers ${WEB_CONCURRENCY:-2} \
      --timeout-keep-alive 5 \
      --log-level ${LOG_LEVEL:-info} \
      --access-log -"]
