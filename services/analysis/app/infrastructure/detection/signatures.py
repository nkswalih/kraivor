"""Technology signature mappings for framework/tool detection.

Each mapping links a dependency name found in a config file
to a DetectedTechnology descriptor.
"""

from app.infrastructure.detection.models import DetectedTechnology

# ── Python ──────────────────────────────────────────────────────────────────

PYTHON_FRAMEWORKS: dict[str, DetectedTechnology] = {
    "django": DetectedTechnology(name="Django", category="framework", detected_from="pyproject.toml|requirements.txt"),
    "djangorestframework": DetectedTechnology(name="Django REST Framework", category="framework", detected_from="pyproject.toml|requirements.txt"),
    "fastapi": DetectedTechnology(name="FastAPI", category="framework", detected_from="pyproject.toml|requirements.txt"),
    "flask": DetectedTechnology(name="Flask", category="framework", detected_from="pyproject.toml|requirements.txt"),
    "sqlalchemy": DetectedTechnology(name="SQLAlchemy", category="framework", detected_from="pyproject.toml|requirements.txt"),
    "celery": DetectedTechnology(name="Celery", category="framework", detected_from="pyproject.toml|requirements.txt"),
    "redis": DetectedTechnology(name="Redis", category="database", detected_from="pyproject.toml|requirements.txt"),
    "pytest": DetectedTechnology(name="Pytest", category="tool", detected_from="pyproject.toml|requirements.txt"),
    "pydantic": DetectedTechnology(name="Pydantic", category="framework", detected_from="pyproject.toml|requirements.txt"),
    "gunicorn": DetectedTechnology(name="Gunicorn", category="tool", detected_from="pyproject.toml|requirements.txt"),
    "uvicorn": DetectedTechnology(name="Uvicorn", category="tool", detected_from="pyproject.toml|requirements.txt"),
    "rq": DetectedTechnology(name="RQ", category="framework", detected_from="pyproject.toml|requirements.txt"),
}

# ── JavaScript / TypeScript (Node) ──────────────────────────────────────────

NODE_FRAMEWORKS: dict[str, DetectedTechnology] = {
    "express": DetectedTechnology(name="Express", category="framework", detected_from="package.json"),
    "next": DetectedTechnology(name="Next.js", category="framework", detected_from="package.json"),
    "@nestjs/core": DetectedTechnology(name="NestJS", category="framework", detected_from="package.json"),
    "fastify": DetectedTechnology(name="Fastify", category="framework", detected_from="package.json"),
    "koa": DetectedTechnology(name="Koa", category="framework", detected_from="package.json"),
    "hono": DetectedTechnology(name="Hono", category="framework", detected_from="package.json"),
    "prisma": DetectedTechnology(name="Prisma", category="tool", detected_from="package.json"),
    "@prisma/client": DetectedTechnology(name="Prisma", category="tool", detected_from="package.json"),
    "typeorm": DetectedTechnology(name="TypeORM", category="tool", detected_from="package.json"),
    "mongoose": DetectedTechnology(name="Mongoose", category="tool", detected_from="package.json"),
    "sequelize": DetectedTechnology(name="Sequelize", category="tool", detected_from="package.json"),
    "bull": DetectedTechnology(name="Bull", category="framework", detected_from="package.json"),
    "bullmq": DetectedTechnology(name="BullMQ", category="framework", detected_from="package.json"),
    "socket.io": DetectedTechnology(name="Socket.IO", category="framework", detected_from="package.json"),
}

# ── Frontend / Fullstack ────────────────────────────────────────────────────

FRONTEND_FRAMEWORKS: dict[str, DetectedTechnology] = {
    "react": DetectedTechnology(name="React", category="framework", detected_from="package.json"),
    "next": DetectedTechnology(name="Next.js", category="framework", detected_from="package.json"),
    "vue": DetectedTechnology(name="Vue", category="framework", detected_from="package.json"),
    "nuxt": DetectedTechnology(name="Nuxt", category="framework", detected_from="package.json"),
    "@angular/core": DetectedTechnology(name="Angular", category="framework", detected_from="package.json"),
    "vite": DetectedTechnology(name="Vite", category="tool", detected_from="package.json"),
    "redux": DetectedTechnology(name="Redux", category="tool", detected_from="package.json"),
    "zustand": DetectedTechnology(name="Zustand", category="tool", detected_from="package.json"),
}

# ── Go ──────────────────────────────────────────────────────────────────────

GO_FRAMEWORKS: dict[str, DetectedTechnology] = {
    "github.com/gin-gonic/gin": DetectedTechnology(name="Gin", category="framework", detected_from="go.mod"),
    "github.com/gofiber/fiber/v2": DetectedTechnology(name="Fiber", category="framework", detected_from="go.mod"),
    "github.com/labstack/echo/v4": DetectedTechnology(name="Echo", category="framework", detected_from="go.mod"),
    "github.com/go-chi/chi/v5": DetectedTechnology(name="Chi", category="framework", detected_from="go.mod"),
    "gorm.io/gorm": DetectedTechnology(name="GORM", category="tool", detected_from="go.mod"),
}

# ── Infrastructure / DevOps signals ─────────────────────────────────────────

INFRA_SIGNALS: dict[str, DetectedTechnology] = {
    "dockerfile": DetectedTechnology(name="Docker", category="infra", detected_from="Dockerfile"),
    "docker_compose": DetectedTechnology(name="Docker Compose", category="infra", detected_from="docker-compose.yml|docker-compose.yaml"),
    "kubernetes": DetectedTechnology(name="Kubernetes", category="infra", detected_from="*.yaml|*.yml"),
    "postgresql": DetectedTechnology(name="PostgreSQL", category="database", detected_from="config"),
    "mongodb": DetectedTechnology(name="MongoDB", category="database", detected_from="config"),
    "kafka": DetectedTechnology(name="Kafka", category="infra", detected_from="config|dependencies"),
    "rabbitmq": DetectedTechnology(name="RabbitMQ", category="infra", detected_from="config|dependencies"),
    "nginx": DetectedTechnology(name="Nginx", category="infra", detected_from="nginx.conf|Dockerfile"),
    "terraform": DetectedTechnology(name="Terraform", category="infra", detected_from="*.tf"),
}

# ── Aggregated lookups ─────────────────────────────────────────────────────

def _merge_dicts(*dicts: dict) -> dict:
    result: dict = {}
    for d in dicts:
        result.update(d)
    return result

ALL_PACKAGE_JSON_SIGNATURES: dict[str, DetectedTechnology] = _merge_dicts(
    NODE_FRAMEWORKS,
    FRONTEND_FRAMEWORKS,
)

ALL_PYTHON_SIGNATURES: dict[str, DetectedTechnology] = PYTHON_FRAMEWORKS

ALL_GO_SIGNATURES: dict[str, DetectedTechnology] = GO_FRAMEWORKS
