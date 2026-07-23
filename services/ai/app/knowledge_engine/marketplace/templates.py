"""Knowledge Templates — pre-built knowledge bundles for common tech stacks.

Templates are curated knowledge collections that can be imported into
any workspace to get started quickly.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class KnowledgeTemplate:
    """A pre-built knowledge template."""
    template_id: str
    name: str
    description: str
    category: str
    tags: list[str] = field(default_factory=list)
    items: list[dict] = field(default_factory=list)
    author: str = "kraivor"
    version: str = "1.0"


def get_templates() -> list[KnowledgeTemplate]:
    """Return all available knowledge templates."""
    return [
        KnowledgeTemplate(
            template_id="python-web-stack",
            name="Python Web Development Stack",
            description="Knowledge base for Python web development with Django/FastAPI",
            category="web-development",
            tags=["python", "django", "fastapi", "web"],
            items=[
                {
                    "source_url": "template://python-web/fastapi",
                    "source_provider": "template",
                    "title": "FastAPI Best Practices",
                    "content": "FastAPI is a modern, fast web framework for building APIs with Python 3.7+ based on standard Python type hints. Key features: automatic API documentation, dependency injection, WebSocket support, and async/await. Best practices: use Pydantic models for validation, leverage dependency injection for database sessions, implement proper error handlers, use background tasks for heavy operations.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
                {
                    "source_url": "template://python-web/django",
                    "source_provider": "template",
                    "title": "Django Best Practices",
                    "content": "Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design. Best practices: use class-based views, implement proper URL routing, use Django ORM effectively, implement caching strategies, use Django REST Framework for APIs, follow the 12-factor app methodology.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
                {
                    "source_url": "template://python-web/postgres",
                    "source_provider": "template",
                    "title": "PostgreSQL with Python",
                    "content": "PostgreSQL is the most advanced open-source relational database. Python integration: use asyncpg for async connections, SQLAlchemy for ORM, psycopg2 for synchronous connections. Best practices: use connection pooling, implement proper indexing, use JSONB for flexible schemas, enable pg_stat_statements for query analysis.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
            ],
        ),
        KnowledgeTemplate(
            template_id="javascript-fullstack",
            name="JavaScript Full-Stack Development",
            description="Knowledge base for JavaScript full-stack with React/Next.js/Node.js",
            category="web-development",
            tags=["javascript", "react", "nextjs", "nodejs", "fullstack"],
            items=[
                {
                    "source_url": "template://js-fullstack/react",
                    "source_provider": "template",
                    "title": "React Best Practices",
                    "content": "React is a JavaScript library for building user interfaces. Best practices: use functional components with hooks, implement proper state management (Context/Redux/Zustand), use React Query for server state, implement code splitting with React.lazy, follow the component composition pattern, use TypeScript for type safety.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
                {
                    "source_url": "template://js-fullstack/nextjs",
                    "source_provider": "template",
                    "title": "Next.js Best Practices",
                    "content": "Next.js is a React framework for production. Features: server-side rendering, static site generation, API routes, middleware, image optimization. Best practices: use App Router for new projects, implement proper loading states, use Server Components when possible, implement ISR for dynamic content, use next/font for font optimization.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
                {
                    "source_url": "template://js-fullstack/nodejs",
                    "source_provider": "template",
                    "title": "Node.js Backend Best Practices",
                    "content": "Node.js runtime for server-side JavaScript. Best practices: use Express/Fastify for HTTP, implement proper error handling, use worker threads for CPU-intensive tasks, implement rate limiting, use PM2 for process management, implement health checks, use structured logging with Winston/Pino.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
            ],
        ),
        KnowledgeTemplate(
            template_id="devops-fundamentals",
            name="DevOps Fundamentals",
            description="Knowledge base for Docker, Kubernetes, CI/CD, and cloud deployment",
            category="devops",
            tags=["docker", "kubernetes", "ci-cd", "cloud", "devops"],
            items=[
                {
                    "source_url": "template://devops/docker",
                    "source_provider": "template",
                    "title": "Docker Best Practices",
                    "content": "Docker containers for consistent development and deployment. Best practices: use multi-stage builds, minimize image layers, use .dockerignore, run as non-root user, use health checks, implement proper secrets management, use Docker Compose for local development, scan images for vulnerabilities.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
                {
                    "source_url": "template://devops/kubernetes",
                    "source_provider": "template",
                    "title": "Kubernetes Deployment Guide",
                    "content": "Kubernetes for container orchestration. Key concepts: Pods, Deployments, Services, Ingress, ConfigMaps, Secrets. Best practices: use Helm charts for packaging, implement proper resource limits, use namespaces for isolation, implement rolling updates, use liveness/readiness probes, monitor with Prometheus/Grafana.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
                {
                    "source_url": "template://devops/ci-cd",
                    "source_provider": "template",
                    "title": "CI/CD Pipeline Best Practices",
                    "content": "Continuous Integration and Deployment. Best practices: automate testing (unit, integration, e2e), use feature branches, implement code review, use semantic versioning, implement canary deployments, use infrastructure as code (Terraform/Pulumi), implement proper rollback strategies, monitor deployment health.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
            ],
        ),
        KnowledgeTemplate(
            template_id="ai-ml-fundamentals",
            name="AI/ML Development Stack",
            description="Knowledge base for machine learning, LLMs, and AI engineering",
            category="ai-ml",
            tags=["ai", "ml", "llm", "python", "tensorflow", "pytorch"],
            items=[
                {
                    "source_url": "template://ai-ml/llm",
                    "source_provider": "template",
                    "title": "LLM Integration Best Practices",
                    "content": "Large Language Model integration patterns. Best practices: implement proper prompt engineering, use RAG for knowledge-augmented generation, implement proper token management, use streaming for better UX, implement guardrails and safety filters, use function calling for structured outputs, implement proper caching strategies.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
                {
                    "source_url": "template://ai-ml/mlops",
                    "source_provider": "template",
                    "title": "MLOps Best Practices",
                    "content": "Machine Learning Operations. Best practices: use MLflow/Weights & Biases for experiment tracking, implement proper data versioning, use feature stores, implement model monitoring, use A/B testing for model evaluation, implement proper model versioning, use containerization for model deployment.",
                    "trust_score": 0.9,
                    "source_type": "text",
                },
            ],
        ),
    ]
