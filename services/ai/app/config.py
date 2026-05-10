from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://kraivor:kraivor@localhost:5432/kraivor"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"

    # KRV-012: JWT Configuration
    identity_jwks_url: str = "http://identity:8001/.well-known/jwks.json"
    jwt_algorithm: str = "RS256"
    jwt_audience: str = "kraivor"
    jwt_issuer: str = "kraivor-identity"
    jwt_verify_expiration: bool = True
    jwt_jwks_cache_ttl: int = 3600

    # Internal request header
    internal_request_header: str = "X-Internal-Request"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()