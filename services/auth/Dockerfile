FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc curl && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml /app/
RUN uv sync --frozen --no-dev

COPY . /app/

EXPOSE 8001

CMD ["gunicorn", "identity.wsgi:application", "--bind", "0.0.0.0:8001"]
