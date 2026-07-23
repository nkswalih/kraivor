from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import JWTPayload, get_current_user
from app.api.schemas.embeddings import (
    EmbeddingData,
    EmbeddingRequest,
    EmbeddingResponse,
    EmbeddingUsage,
)
from app.infrastructure.rag.embedder import Embedder

CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]

router = APIRouter(tags=["embeddings"])

embedder = Embedder()


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(request: EmbeddingRequest, user: CurrentUser):
    inputs = [request.input] if isinstance(request.input, str) else request.input
    embeddings = await embedder.embed_batch(inputs)

    data = [EmbeddingData(index=i, embedding=emb) for i, emb in enumerate(embeddings)]

    return EmbeddingResponse(
        data=data,
        model="all-MiniLM-L6-v2",
        usage=EmbeddingUsage(prompt_tokens=sum(len(t.split()) for t in inputs)),
    )
