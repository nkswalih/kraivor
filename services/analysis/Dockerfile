FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc git curl && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY --from=ghcr.io/astral-sh/uv:0.11.7 /uv /uvx /bin/

COPY pyproject.toml uv.lock /app/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY . /app/

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser && \
    chown -R appuser:appgroup /app
USER appuser

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
