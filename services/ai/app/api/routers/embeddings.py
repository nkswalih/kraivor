from fastapi import APIRouter, Depends, HTTPException
from app.api.dependencies.auth import get_current_user, JWTPayload
from app.api.schemas.embeddings import EmbeddingRequest, EmbeddingResponse, EmbeddingData, EmbeddingUsage
from app.infrastructure.rag.embedder import Embedder

router = APIRouter(tags=["embeddings"])

embedder = Embedder()


@router.post("/embeddings", response_model=EmbeddingResponse)
async def create_embeddings(
    request: EmbeddingRequest,
    user: JWTPayload = Depends(get_current_user),
):
    inputs = [request.input] if isinstance(request.input, str) else request.input
    embeddings = await embedder.embed_batch(inputs)

    data = [
        EmbeddingData(index=i, embedding=emb)
        for i, emb in enumerate(embeddings)
    ]

    return EmbeddingResponse(
        data=data,
        model="all-MiniLM-L6-v2",
        usage=EmbeddingUsage(prompt_tokens=sum(len(t.split()) for t in inputs)),
    )
