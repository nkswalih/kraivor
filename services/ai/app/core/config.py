from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="AI_",
    )

    # Database
    database__url: str = "postgresql+asyncpg://kraivor:kraivor@localhost:5433/kraivor"

    # Redis
    redis__url: str = "redis://localhost:6379/0"

    # Celery
    celery__broker__url: str = "redis://localhost:6379/1"
    celery__result__backend: str = "redis://localhost:6379/1"

    # Kafka
    kafka__bootstrap__servers: str = "localhost:9092"

    # Identity / Auth
    identity__jwks__url: str = "http://identity:8001/.well-known/jwks.json"
    jwt_algorithm: str = "RS256"
    jwt_audience: str = "kraivor"
    jwt_issuer: str = "kraivor-identity"
    jwt_verify_expiration: bool = True
    jwt_jwks_cache_ttl: int = 3600
    internal_request_header: str = "X-Internal-Request"

    # LLM Provider
    openrouter__master__key: str = ""
    openrouter_site_url: str = "https://kraivor.com"
    openrouter_app_name: str = "Kraivor"

    # Encryption for stored provider keys
    key_encryption_key: str = ""

    # Embedding
    embedding_provider: str = "local"
    embedding_model: str = "all-MiniLM-L6-v2"

    # Inter-service communication
    core_api_url: str = "http://core:8002/api"
    analysis_api_url: str = "http://analysis:8003/api/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8004
    debug: bool = False


settings = Settings()
