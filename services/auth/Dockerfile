# =============================================================================
# Dockerfile — Auth Service (Production)
# =============================================================================
# Multi-stage build:
#   Stage 1 (builder) — install deps into an isolated venv via uv
#   Stage 2 (runtime) — copy only the venv + app code, no build tools
#
# Result: lean final image (~180MB vs ~600MB single-stage)
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
# If pyproject.toml + uv.lock haven't changed, this layer is cached
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

# Copy venv from builder (no uv, no gcc, no curl in runtime)
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY --from=builder /app /app

# Put venv on PATH — no `source activate` needed
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Collect static files at build time
# (requires SECRET_KEY at build — use a dummy value here, overridden at runtime)
RUN SECRET_KEY=build-time-placeholder \
    DATABASE_URL=sqlite:///dev-null \
    python manage.py collectstatic --noinput --clear 2>/dev/null || true

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8001

# Gunicorn: 2 workers per CPU core is the standard starting point
# Adjust WEB_CONCURRENCY env var at runtime without rebuilding
CMD ["sh", "-c", \
     "gunicorn auth.wsgi:application \
      --bind 0.0.0.0:8001 \
      --workers ${WEB_CONCURRENCY:-2} \
      --threads ${WEB_THREADS:-2} \
      --worker-class gthread \
      --worker-tmp-dir /dev/shm \
      --timeout 30 \
      --keep-alive 5 \
      --log-level ${LOG_LEVEL:-info} \
      --access-logfile - \
      --error-logfile -"]