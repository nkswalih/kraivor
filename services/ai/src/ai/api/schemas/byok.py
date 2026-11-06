from datetime import datetime

from pydantic import BaseModel


class ModelProviderOption(BaseModel):
    provider: str
    name: str
    default_base_url: str


class ByokModelConfig(BaseModel):
    model_id: str
    model_name: str
    backend_model: str
    available_providers: list[ModelProviderOption]
    selected_provider: str | None = None
    has_key: bool = False
    custom_url: str | None = None
    last_validated: datetime | None = None


class ProviderStatus(BaseModel):
    provider: str
    name: str
    has_key: bool
    model_count: int
    models: list[str]
    custom_url: str | None = None
    last_validated: datetime | None = None


class ProviderKeyUpdate(BaseModel):
    api_key: str
    custom_url: str | None = None


class ValidateResult(BaseModel):
    valid: bool
    error: str | None = None
    models: list[str] = []
    rate_limit: dict | None = None


class ModelProviderUpdate(BaseModel):
    provider: str
