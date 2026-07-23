import pytest

from app.api.schemas.embeddings import EmbeddingRequest, EmbeddingResponse

pytestmark = pytest.mark.unit


class TestEmbeddingsRouter:
    async def test_embedding_request_schema(self):
        req = EmbeddingRequest(input="hello world")
        assert req.input == "hello world"

    async def test_embedding_response_schema(self):
        from app.api.schemas.embeddings import EmbeddingData, EmbeddingUsage

        resp = EmbeddingResponse(
            data=[EmbeddingData(index=0, embedding=[0.1, 0.2, 0.3])],
            model="test",
            usage=EmbeddingUsage(prompt_tokens=2),
        )
        assert len(resp.data) == 1
        assert resp.data[0].index == 0
