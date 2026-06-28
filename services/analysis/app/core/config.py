from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseModel):
    name: str = "analysis-service"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False


class DatabaseSettings(BaseModel):
    url: SecretStr
    pool_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=20, ge=0)
    pool_recycle: int = Field(default=1800, ge=1)
    echo: bool = False


class RedisSettings(BaseModel):
    url: str = "redis://localhost:6379/0"
    socket_timeout: int = Field(default=5, ge=1)
    retry_on_timeout: bool = True


class S3Settings(BaseModel):
    endpoint_url: str | None = None
    access_key_id: str = ""
    secret_access_key: SecretStr = SecretStr("")
    region: str = "us-east-1"
    reports_bucket: str = "kraivor-reports"
    use_ssl: bool = True


class JWTSettings(BaseModel):
    jwks_url: str = "http://identity:8001/.well-known/jwks.json"
    algorithm: Literal[
        "RS256", "RS384", "RS512",
        "ES256", "ES384", "ES512",
    ] = "RS256"
    audience: str = "kraivor"
    issuer: str = "kraivor-identity"
    verify_expiration: bool = True
    jwks_cache_ttl: int = Field(default=3600, ge=0)
    internal_request_header: str = "X-Internal-Request"


class GitSettings(BaseModel):
    clone_depth: int = Field(default=1, ge=1)
    clone_timeout: int = Field(default=120, ge=1)
    token: SecretStr = SecretStr("")


class AnalysisSettings(BaseModel):
    default_branch: str = "main"
    simulate_users: list[int] = [100, 500, 5000, 50000]
    max_file_size_bytes: int = Field(default=1_000_000, ge=1)
    ephemeral_path: str = "/tmp/analysis"


class ScoringSettings(BaseModel):
    performance_weight: float = Field(default=0.25, ge=0, le=1)
    security_weight: float = Field(default=0.25, ge=0, le=1)
    reliability_weight: float = Field(default=0.20, ge=0, le=1)
    maintainability_weight: float = Field(default=0.15, ge=0, le=1)
    devops_weight: float = Field(default=0.15, ge=0, le=1)

    @model_validator(mode="after")
    def _weights_must_sum_to_one(self) -> "ScoringSettings":
        total = (
            self.performance_weight
            + self.security_weight
            + self.reliability_weight
            + self.maintainability_weight
            + self.devops_weight
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"Scoring weights must sum to 1.0, got {total:.4f}"
            )
        return self


class RPMSettings(BaseModel):
    base_per_endpoint: int = Field(default=2000, ge=0)
    n_plus_one_deduction: int = Field(default=400, ge=0)
    sync_call_deduction: int = Field(default=200, ge=0)
    unbounded_query_deduction: int = Field(default=300, ge=0)


class KafkaSettings(BaseModel):
    bootstrap_servers: str = "localhost:9092"
    analysis_events_topic: str = "analysis.events"
    consumer_group: str = "analysis-service"


class OTelSettings(BaseModel):
    service_name: str = "analysis-service"
    exporter_otlp_endpoint: str = "http://otel-collector:4318"
    traces_sampler: Literal[
        "always_on", "always_off", "parent_based", "trace_id_ratio"
    ] = "always_on"
    traces_sample_rate: float = Field(default=1.0, ge=0, le=1)


class MonitoringSettings(BaseModel):
    enabled: bool = True
    port: int = Field(default=8003, ge=1024, le=65535)


class LoggingSettings(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_format: bool = True


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="ANALYSIS_",
        env_nested_delimiter="__",
    )

    service: ServiceSettings = ServiceSettings()
    database: DatabaseSettings
    redis: RedisSettings = RedisSettings()
    s3: S3Settings = S3Settings()
    jwt: JWTSettings = JWTSettings()
    git: GitSettings = GitSettings()
    analysis: AnalysisSettings = AnalysisSettings()
    scoring: ScoringSettings = ScoringSettings()
    rpm: RPMSettings = RPMSettings()
    kafka: KafkaSettings = KafkaSettings()
    otel: OTelSettings = OTelSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    logging: LoggingSettings = LoggingSettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
