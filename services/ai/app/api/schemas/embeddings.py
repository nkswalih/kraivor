from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    input: str | list[str] = Field(..., description="Text or texts to embed")
    model: str | None = Field(None, description="Embedding model override")


class EmbeddingData(BaseModel):
    object: str = "embedding"
    index: int
    embedding: list[float]


class EmbeddingUsage(BaseModel):
    prompt_tokens: int = 0
    total_tokens: int = 0


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingData]
    model: str
    usage: EmbeddingUsage
