from app.infrastructure.rag.chunker import SemanticChunker
from app.infrastructure.rag.embedder import Embedder
from sqlalchemy import text


class Indexer:
    def __init__(self, chunker: SemanticChunker | None = None, embedder: Embedder | None = None):
        self.chunker = chunker or SemanticChunker()
        self.embedder = embedder or Embedder()

    async def index_file(
        self,
        db_session,
        repo_id: str,
        workspace_id: str,
        file_path: str,
        content: str,
        language: str,
    ) -> list[dict]:
        chunks = await self.chunker.chunk_file(file_path, content, language)
        texts = [c["content"] for c in chunks]
        embeddings = await self.embedder.embed_batch(texts)

        indexed = []
        for chunk, emb in zip(chunks, embeddings):
            chunk_id = f"{repo_id}_{chunk['file_path']}_{chunk['start_line']}"
            await db_session.execute(
                text("""
                    INSERT INTO ai.code_embeddings
                        (id, repo_id, workspace_id, file_path, language,
                         content, embedding, line_start, line_end)
                    VALUES
                        (:id, :repo_id, :workspace_id, :file_path, :language,
                         :content, :embedding, :line_start, :line_end)
                    ON CONFLICT (id) DO UPDATE SET
                        embedding = :embedding,
                        content = :content
                """),
                {
                    "id": chunk_id,
                    "repo_id": repo_id,
                    "workspace_id": workspace_id,
                    "file_path": chunk["file_path"],
                    "language": chunk["language"],
                    "content": chunk["content"][:2000],
                    "embedding": emb,
                    "line_start": chunk["start_line"],
                    "line_end": chunk["end_line"],
                },
            )
            indexed.append({"id": chunk_id, **chunk})

        return indexed
