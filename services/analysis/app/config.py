from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    database_url: str

    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"

    identity_jwks_url: str = "http://identity:8001/.well-known/jwks.json"
    jwt_algorithm: str = "RS256"
    jwt_audience: str = "kraivor"
    jwt_issuer: str = "kraivor-identity"
    jwt_verify_expiration: bool = True
    jwt_jwks_cache_ttl: int = 3600

    internal_request_header: str = "X-Internal-Request"


settings = Settings()