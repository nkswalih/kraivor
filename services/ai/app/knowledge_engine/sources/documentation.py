"""Documentation provider — curated official docs for 50+ frameworks."""

from __future__ import annotations

import logging
import re

from app.knowledge_engine.sources.base import SourceResult, SourceContent

logger = logging.getLogger(__name__)

# Curated documentation sources with trust scores
DOCUMENTATION_SOURCES: dict[str, dict] = {
    # Python
    "python": {"url": "https://docs.python.org/3/", "trust": 0.95, "name": "Python Documentation"},
    "django": {"url": "https://docs.djangoproject.com/", "trust": 0.95, "name": "Django Documentation"},
    "fastapi": {"url": "https://fastapi.tiangolo.com/", "trust": 0.95, "name": "FastAPI Documentation"},
    "flask": {"url": "https://flask.palletsprojects.com/", "trust": 0.90, "name": "Flask Documentation"},
    "sqlalchemy": {"url": "https://docs.sqlalchemy.org/", "trust": 0.90, "name": "SQLAlchemy Documentation"},
    "celery": {"url": "https://docs.celeryq.dev/", "trust": 0.85, "name": "Celery Documentation"},
    "pydantic": {"url": "https://docs.pydantic.dev/", "trust": 0.90, "name": "Pydantic Documentation"},

    # Frontend
    "react": {"url": "https://react.dev/", "trust": 0.95, "name": "React Documentation"},
    "nextjs": {"url": "https://nextjs.org/docs", "trust": 0.95, "name": "Next.js Documentation"},
    "vue": {"url": "https://vuejs.org/guide/", "trust": 0.90, "name": "Vue.js Documentation"},
    "angular": {"url": "https://angular.dev/", "trust": 0.90, "name": "Angular Documentation"},
    "svelte": {"url": "https://svelte.dev/docs/", "trust": 0.90, "name": "Svelte Documentation"},
    "tailwind": {"url": "https://tailwindcss.com/docs", "trust": 0.90, "name": "Tailwind CSS Documentation"},
    "typescript": {"url": "https://www.typescriptlang.org/docs/", "trust": 0.95, "name": "TypeScript Documentation"},

    # DevOps
    "docker": {"url": "https://docs.docker.com/", "trust": 0.95, "name": "Docker Documentation"},
    "kubernetes": {"url": "https://kubernetes.io/docs/", "trust": 0.95, "name": "Kubernetes Documentation"},
    "terraform": {"url": "https://developer.hashicorp.com/terraform/docs", "trust": 0.90, "name": "Terraform Documentation"},
    "ansible": {"url": "https://docs.ansible.com/", "trust": 0.85, "name": "Ansible Documentation"},
    "github_actions": {"url": "https://docs.github.com/en/actions", "trust": 0.95, "name": "GitHub Actions Documentation"},

    # Cloud
    "aws": {"url": "https://docs.aws.amazon.com/", "trust": 0.95, "name": "AWS Documentation"},
    "gcp": {"url": "https://cloud.google.com/docs", "trust": 0.95, "name": "Google Cloud Documentation"},
    "azure": {"url": "https://learn.microsoft.com/azure/", "trust": 0.95, "name": "Azure Documentation"},

    # AI/ML
    "openai": {"url": "https://platform.openai.com/docs", "trust": 0.95, "name": "OpenAI Documentation"},
    "anthropic": {"url": "https://docs.anthropic.com/", "trust": 0.95, "name": "Anthropic Documentation"},
    "langchain": {"url": "https://python.langchain.com/", "trust": 0.90, "name": "LangChain Documentation"},
    "llamaindex": {"url": "https://docs.llamaindex.ai/", "trust": 0.90, "name": "LlamaIndex Documentation"},
    "huggingface": {"url": "https://huggingface.co/docs", "trust": 0.90, "name": "Hugging Face Documentation"},
    "pytorch": {"url": "https://pytorch.org/docs/stable/", "trust": 0.95, "name": "PyTorch Documentation"},
    "tensorflow": {"url": "https://www.tensorflow.org/guide", "trust": 0.90, "name": "TensorFlow Documentation"},

    # Databases
    "postgresql": {"url": "https://www.postgresql.org/docs/", "trust": 0.95, "name": "PostgreSQL Documentation"},
    "redis": {"url": "https://redis.io/docs/", "trust": 0.90, "name": "Redis Documentation"},
    "mongodb": {"url": "https://www.mongodb.com/docs/", "trust": 0.90, "name": "MongoDB Documentation"},
    "elasticsearch": {"url": "https://www.elastic.co/guide/", "trust": 0.85, "name": "Elasticsearch Documentation"},
    "sqlite": {"url": "https://www.sqlite.org/docs.html", "trust": 0.90, "name": "SQLite Documentation"},

    # Messaging/Streaming
    "kafka": {"url": "https://kafka.apache.org/documentation/", "trust": 0.90, "name": "Kafka Documentation"},
    "rabbitmq": {"url": "https://www.rabbitmq.com/docs", "trust": 0.85, "name": "RabbitMQ Documentation"},
    "redis_streams": {"url": "https://redis.io/docs/latest/develop/data-types/streams/", "trust": 0.90, "name": "Redis Streams"},

    # Additional
    "nodejs": {"url": "https://nodejs.org/docs/latest/", "trust": 0.95, "name": "Node.js Documentation"},
    "go": {"url": "https://go.dev/doc/", "trust": 0.95, "name": "Go Documentation"},
    "rust": {"url": "https://doc.rust-lang.org/book/", "trust": 0.95, "name": "Rust Book"},
    "java": {"url": "https://docs.oracle.com/en/java/", "trust": 0.90, "name": "Java Documentation"},
    "spring": {"url": "https://docs.spring.io/spring-framework/reference/", "trust": 0.90, "name": "Spring Framework"},
    "supabase": {"url": "https://supabase.com/docs", "trust": 0.85, "name": "Supabase Documentation"},
    "vercel": {"url": "https://vercel.com/docs", "trust": 0.85, "name": "Vercel Documentation"},
    "cloudflare": {"url": "https://developers.cloudflare.com/", "trust": 0.90, "name": "Cloudflare Documentation"},
    "graphql": {"url": "https://graphql.org/learn/", "trust": 0.90, "name": "GraphQL Documentation"},
    "gRPC": {"url": "https://grpc.io/docs/", "trust": 0.85, "name": "gRPC Documentation"},
}

# Keywords to match documentation sources
_KEYWORD_MAP: dict[str, list[str]] = {
    "python": ["python", "pip", "pypi", "cpython"],
    "django": ["django", "djangorestframework", "drf"],
    "fastapi": ["fastapi", "uvicorn", "pydantic"],
    "react": ["react", "reactjs", "jsx", "hooks"],
    "nextjs": ["nextjs", "next.js", "next"],
    "docker": ["docker", "dockerfile", "container", "docker-compose"],
    "kubernetes": ["kubernetes", "k8s", "kubectl", "pod", "deployment"],
    "aws": ["aws", "amazon web services", "lambda", "s3", "ec2", "dynamodb", "sqs", "sns"],
    "gcp": ["gcp", "google cloud", "cloud run", "cloud functions", "bigquery"],
    "azure": ["azure", "microsoft cloud", "azure functions", "cosmos db"],
    "openai": ["openai", "gpt", "chatgpt", "dall-e", "whisper"],
    "anthropic": ["anthropic", "claude"],
    "langchain": ["langchain", "langgraph"],
    "postgresql": ["postgresql", "postgres", "psql", "pg"],
    "redis": ["redis", "valkey"],
    "kafka": ["kafka", "kafka streams", "kafka connect"],
    "nodejs": ["node.js", "nodejs", "express", "nestjs"],
    "typescript": ["typescript", "ts", "tsc"],
    "go": ["golang", "go"],
    "rust": ["rust", "cargo", "rustc"],
    "java": ["java", "spring boot", "spring"],
    "tensorflow": ["tensorflow", "keras"],
    "pytorch": ["pytorch", "torch"],
}


class DocumentationProvider:
    """Curated documentation provider for official framework docs."""

    name = "documentation"
    base_trust_score = 0.90

    async def search(self, query: str, max_results: int = 5) -> list[SourceResult]:
        """Find relevant documentation based on query keywords."""
        query_lower = query.lower()
        matched_sources = []

        # Match query to documentation sources
        for key, keywords in _KEYWORD_MAP.items():
            for keyword in keywords:
                if keyword in query_lower:
                    if key in DOCUMENTATION_SOURCES:
                        doc = DOCUMENTATION_SOURCES[key]
                        matched_sources.append(SourceResult(
                            url=doc["url"],
                            title=doc["name"],
                            snippet=f"Official documentation for {doc['name']}",
                            source_provider=self.name,
                            trust_score=doc["trust"],
                            metadata={"framework": key},
                        ))
                    break

        # Also search for specific topics within matched docs
        if matched_sources:
            for src in matched_sources[:max_results]:
                framework = src.metadata.get("framework", "")
                # Construct a likely topic URL
                topic_url = self._build_topic_url(framework, query_lower)
                if topic_url and topic_url != src.url:
                    matched_sources.append(SourceResult(
                        url=topic_url,
                        title=f"{src.title} — {query}",
                        snippet=f"Documentation section for: {query}",
                        source_provider=self.name,
                        trust_score=src.trust_score,
                        metadata={"framework": framework},
                    ))

        return matched_sources[:max_results]

    async def fetch_content(self, url: str) -> SourceContent | None:
        """Fetch documentation content using trafilatura."""
        try:
            import aiohttp
            import trafilatura

            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                ),
            }

            async with aiohttp.ClientSession(headers=headers) as session, session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=20),
                allow_redirects=True,
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()

            text = trafilatura.extract(
                html,
                include_links=True,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
            )

            if not text:
                return None

            # Extract title
            title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
            title = title_match.group(1).strip() if title_match else url

            if len(text) > 8000:
                text = text[:8000] + "\n\n[Content truncated...]"

            # Determine trust score from URL
            from app.knowledge_engine.config import get_trust_score
            trust = get_trust_score(url)

            return SourceContent(
                url=url,
                title=title,
                text=text,
                source_provider=self.name,
                trust_score=max(trust, self.base_trust_score),
            )
        except Exception as e:
            logger.warning("Failed to fetch documentation from %s: %s", url, e)
            return None

    def _build_topic_url(self, framework: str, query: str) -> str | None:
        """Build a likely documentation topic URL."""
        doc = DOCUMENTATION_SOURCES.get(framework)
        if not doc:
            return None

        base = doc["url"].rstrip("/")

        # Common URL patterns
        topic = query.replace(" ", "-").replace("?", "")
        topic = re.sub(r"[^a-z0-9\-]", "", topic)

        if framework == "django":
            return f"https://docs.djangoproject.com/en/stable/topics/{topic}/"
        if framework == "fastapi":
            return f"https://fastapi.tiangolo.com/tutorial/{topic}/"
        if framework == "react":
            return f"https://react.dev/learn/{topic}"
        if framework == "nextjs":
            return f"https://nextjs.org/docs/{topic}"
        if framework == "docker":
            return f"https://docs.docker.com/engine/reference/builder/#{topic}"
        if framework == "python":
            return f"https://docs.python.org/3/library/{topic}.html"
        if framework == "typescript":
            return f"https://www.typescriptlang.org/docs/handbook/{topic}.html"
        if framework == "kubernetes":
            return f"https://kubernetes.io/docs/concepts/{topic}/"
        if framework == "redis":
            return f"https://redis.io/docs/latest/commands/{topic}/"

        # Generic fallback: append topic to base URL
        return f"{base}/{topic}/"
