FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc git curl && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml /app/
RUN uv sync --frozen --no-dev

COPY . /app/

EXPOSE 8003

CMD alembic -c migrations/alembic.ini upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8003
