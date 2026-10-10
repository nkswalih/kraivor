# =============================================================================
# Dockerfile — Analysis Service (Production)
# =============================================================================
# Multi-stage build (same shape as the other Python services):
#   Stage 1 (builder) — install deps into an isolated venv via uv
#   Stage 2 (runtime) — copy only the venv + app code, no build tools
# =============================================================================

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.14-slim@sha256:0741d101873c12ab927e6f8653feb8862b9bd58771177acb1b885b95141f91b4 AS builder

WORKDIR /app

# System deps needed only at build time
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (pinned version for reproducible builds)
COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

# uv settings
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONDONTWRITEBYTECODE=1

# Copy dependency manifest first — Docker cache layer
COPY pyproject.toml uv.lock /app/

# Install production deps only into /opt/venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Copy application source
COPY . /app/

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.14-slim@sha256:0741d101873c12ab927e6f8653feb8862b9bd58771177acb1b885b95141f91b4 AS runtime

WORKDIR /app

# Runtime system deps (git for repository checkout, curl for the healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Copy venv + application source from the builder (no uv, no gcc)
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

# Put venv on PATH — no `source activate` needed
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8003/v1/health || exit 1

CMD ["uvicorn", "analysis.main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "2"]
