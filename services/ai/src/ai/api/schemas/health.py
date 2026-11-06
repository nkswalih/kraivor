from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "0.1.0"
    service: str = "ai"
