import pytest
from unittest.mock import AsyncMock

from app.infrastructure.rag.chunker import SemanticChunker
from app.infrastructure.rag.embedder import Embedder

pytestmark = pytest.mark.unit


SAMPLE_PYTHON_CODE = """
def hello():
    print("hello world")

class MyClass:
    def method(self):
        pass
"""


class TestChunker:
    async def test_chunk_file_ast_python(self):
        chunker = SemanticChunker()
        chunks = await chunker.chunk_file("test.py", SAMPLE_PYTHON_CODE, "python")
        assert len(chunks) >= 1
        assert all("content" in c for c in chunks)
        assert all("file_path" in c for c in chunks)

    async def test_chunk_fallback_no_ast(self, monkeypatch):
        monkeypatch.setattr(
            "app.infrastructure.rag.chunker.SemanticChunker._chunk_with_ast",
            AsyncMock(side_effect=ImportError),
        )
        chunker = SemanticChunker(chunk_size=100, overlap=10)
        chunks = await chunker.chunk_file("test.txt", "a " * 500, "text")
        assert len(chunks) >= 1


class TestEmbedder:
    async def test_embed_local(self, monkeypatch):
        mock_embedder = AsyncMock()
        mock_embedder.embed = AsyncMock(return_value=[0.1] * 384)

        embedder = Embedder(provider="local")
        monkeypatch.setattr(embedder, "embed", AsyncMock(return_value=[0.1] * 384))

        result = await embedder.embed("hello")
        assert len(result) == 384
