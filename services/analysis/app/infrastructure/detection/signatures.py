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

# ── C# / .NET ─────────────────────────────────────────────────────────────────

CSHARP_FRAMEWORKS: dict[str, DetectedTechnology] = {
    "microsoft.aspnetcore.app": DetectedTechnology(name="ASP.NET Core", category="framework", detected_from="*.csproj"),
    "microsoft.aspnetcore.mvc": DetectedTechnology(name="ASP.NET Core MVC", category="framework", detected_from="*.csproj"),
    "microsoft.entityframeworkcore": DetectedTechnology(name="Entity Framework Core", category="framework", detected_from="*.csproj"),
    "microsoft.entityframeworkcore.sqlserver": DetectedTechnology(name="EF Core SQL Server", category="tool", detected_from="*.csproj"),
    "microsoft.entityframeworkcore.postgresql": DetectedTechnology(name="EF Core PostgreSQL", category="tool", detected_from="*.csproj"),
    "microsoft.entityframeworkcore.inmemory": DetectedTechnology(name="EF Core InMemory", category="tool", detected_from="*.csproj"),
    "dapper": DetectedTechnology(name="Dapper", category="tool", detected_from="*.csproj"),
    "nhibernate": DetectedTechnology(name="NHibernate", category="framework", detected_from="*.csproj"),
    "automapper": DetectedTechnology(name="AutoMapper", category="tool", detected_from="*.csproj"),
    "fluentvalidation": DetectedTechnology(name="FluentValidation", category="tool", detected_from="*.csproj"),
    "serilog": DetectedTechnology(name="Serilog", category="tool", detected_from="*.csproj"),
    "nlog": DetectedTechnology(name="NLog", category="tool", detected_from="*.csproj"),
    "swashbuckle.aspnetcore": DetectedTechnology(name="Swashbuckle (Swagger)", category="tool", detected_from="*.csproj"),
    "nspec": DetectedTechnology(name="NSpec", category="tool", detected_from="*.csproj"),
    "xunit": DetectedTechnology(name="xUnit", category="tool", detected_from="*.csproj"),
    "nunit": DetectedTechnology(name="NUnit", category="tool", detected_from="*.csproj"),
    "moq": DetectedTechnology(name="Moq", category="tool", detected_from="*.csproj"),
    "masstransit": DetectedTechnology(name="MassTransit", category="framework", detected_from="*.csproj"),
    "hangfire": DetectedTechnology(name="Hangfire", category="framework", detected_from="*.csproj"),
    "signalr": DetectedTechnology(name="SignalR", category="framework", detected_from="*.csproj"),
    "grpc.aspnetcore": DetectedTechnology(name="gRPC .NET", category="framework", detected_from="*.csproj"),
    "hotchocolate": DetectedTechnology(name="HotChocolate (GraphQL)", category="framework", detected_from="*.csproj"),
    "microsoft.aspnetcore.identity": DetectedTechnology(name="ASP.NET Core Identity", category="framework", detected_from="*.csproj"),
    "microsoft.aspnetcore.authentication.jwtbearer": DetectedTechnology(name="JWT Bearer", category="tool", detected_from="*.csproj"),
}

ALL_CSHARP_SIGNATURES: dict[str, DetectedTechnology] = CSHARP_FRAMEWORKS

# ── Java ──────────────────────────────────────────────────────────────────────

JAVA_FRAMEWORKS: dict[str, DetectedTechnology] = {
    "org.springframework.boot": DetectedTechnology(name="Spring Boot", category="framework", detected_from="pom.xml|build.gradle"),
    "org.springframework": DetectedTechnology(name="Spring Framework", category="framework", detected_from="pom.xml|build.gradle"),
    "org.springframework.security": DetectedTechnology(name="Spring Security", category="framework", detected_from="pom.xml|build.gradle"),
    "org.springframework.data:spring-data-jpa": DetectedTechnology(name="Spring Data JPA", category="framework", detected_from="pom.xml|build.gradle"),
    "org.hibernate.orm:hibernate-core": DetectedTechnology(name="Hibernate ORM", category="framework", detected_from="pom.xml|build.gradle"),
    "com.zaxxer.hikaricp": DetectedTechnology(name="HikariCP", category="tool", detected_from="pom.xml|build.gradle"),
    "com.fasterxml.jackson.core": DetectedTechnology(name="Jackson", category="tool", detected_from="pom.xml|build.gradle"),
    "org.mybatis": DetectedTechnology(name="MyBatis", category="framework", detected_from="pom.xml|build.gradle"),
    "org.apache.struts": DetectedTechnology(name="Apache Struts", category="framework", detected_from="pom.xml|build.gradle"),
    "jakarta.persistence": DetectedTechnology(name="Jakarta Persistence (JPA)", category="framework", detected_from="pom.xml|build.gradle"),
    "jakarta.validation": DetectedTechnology(name="Jakarta Validation", category="tool", detected_from="pom.xml|build.gradle"),
    "org.projectlombok": DetectedTechnology(name="Lombok", category="tool", detected_from="pom.xml|build.gradle"),
    "org.mapstruct": DetectedTechnology(name="MapStruct", category="tool", detected_from="pom.xml|build.gradle"),
    "org.apache.kafka": DetectedTechnology(name="Kafka Client", category="infra", detected_from="pom.xml|build.gradle"),
    "org.springdoc": DetectedTechnology(name="SpringDoc (Swagger)", category="tool", detected_from="pom.xml|build.gradle"),
    "io.swagger": DetectedTechnology(name="Swagger", category="tool", detected_from="pom.xml|build.gradle"),
    "org.junit.jupiter": DetectedTechnology(name="JUnit 5", category="tool", detected_from="pom.xml|build.gradle"),
    "org.mockito": DetectedTechnology(name="Mockito", category="tool", detected_from="pom.xml|build.gradle"),
    "io.micrometer": DetectedTechnology(name="Micrometer", category="tool", detected_from="pom.xml|build.gradle"),
    "org.flywaydb": DetectedTechnology(name="Flyway", category="tool", detected_from="pom.xml|build.gradle"),
    "org.liquibase": DetectedTechnology(name="Liquibase", category="tool", detected_from="pom.xml|build.gradle"),
    "com.google.guava": DetectedTechnology(name="Guava", category="tool", detected_from="pom.xml|build.gradle"),
    "ch.qos.logback": DetectedTechnology(name="Logback", category="tool", detected_from="pom.xml|build.gradle"),
    "org.apache.logging.log4j": DetectedTechnology(name="Log4j", category="tool", detected_from="pom.xml|build.gradle"),
}

ALL_JAVA_SIGNATURES: dict[str, DetectedTechnology] = JAVA_FRAMEWORKS
