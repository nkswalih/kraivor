from datetime import datetime
from pydantic import BaseModel, Field


class CreateKeyRequest(BaseModel):
    name: str = Field(..., description="Key name")
    scopes: list[str] | None = Field(None, description="Key scopes")
    rate_limit_rpm: int | None = Field(None, description="Rate limit per minute")


class ProvisionRequest(BaseModel):
    provider: str = Field(..., description="Provider name: openrouter, groq, google")
    tier: str | None = Field(None, description="Tier: free, pro, enterprise")


class KeyResponse(BaseModel):
    id: str
    key: str
    prefix: str
    scopes: list[str]
    rate_limit_rpm: int
    created_at: datetime


class ProvisionResponse(BaseModel):
    provider: str
    model_access: list[str]
    rate_limit: dict
    provisioned_at: str
