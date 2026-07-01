# =============================================================================
# Dockerfile — AI Service (Development)
# =============================================================================
# Goals:
#   - Fast container startup
#   - Hot reload support (uvicorn --reload)
#   - Stable uv-based environment
#   - CPU-only torch (no CUDA/nvidia packages)
#   - Source mounted via volume
#   - venv isolated outside /app
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# =============================================================================
# SYSTEM DEPENDENCIES
# =============================================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# INSTALL UV
# =============================================================================

COPY --from=ghcr.io/astral-sh/uv:0.4.30 /uv /usr/local/bin/uv

# =============================================================================
# ENVIRONMENT
# =============================================================================
# UV_PROJECT_ENVIRONMENT=/opt/venv keeps the venv OUTSIDE /app
# so the bind mount ./services/ai:/app does NOT shadow it
# =============================================================================

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH"

# Use CPU-only PyTorch (prevents pulling ~500MB of nvidia CUDA libs)
ENV UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

# =============================================================================
# DEPENDENCY LAYER
# =============================================================================

# Cached unless pyproject changes
COPY pyproject.toml uv.lock /app/

# Install ALL deps (including dev: pytest, ruff, etc.)
RUN uv sync --frozen --no-dev

# =============================================================================
# APPLICATION SOURCE
# =============================================================================

COPY . /app/

# =============================================================================
# EXPOSE
# =============================================================================

EXPOSE 8004

# =============================================================================
# HEALTHCHECK
# =============================================================================

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8004/v1/health || exit 1

# =============================================================================
# STARTUP — uvicorn with hot reload
# =============================================================================

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8004", "--reload"]
