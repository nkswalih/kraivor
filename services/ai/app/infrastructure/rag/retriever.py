from datetime import datetime
from app.infrastructure.rag.embedder import Embedder
from sqlalchemy import text


class Retriever:
    def __init__(self, embedder: Embedder, db_session_factory):
        self.embedder = embedder
        self.db = db_session_factory

    async def retrieve(
        self,
        query: str,
        repo_ids: list[str] | None = None,
        workspace_id: str | None = None,
        top_k: int = 8,
        min_score: float = 0.5,
    ) -> list[dict]:
        query_embedding = await self.embedder.embed(query)

        filters = []
        params = {
            "query_embedding": query_embedding,
            "top_k": top_k * 2,
            "min_score": min_score,
        }

        if repo_ids:
            filters.append("repo_id = ANY(:repo_ids)")
            params["repo_ids"] = repo_ids
        if workspace_id:
            filters.append("workspace_id = :workspace_id")
            params["workspace_id"] = workspace_id

        where_clause = " AND ".join(filters) if filters else "TRUE"

        async with self.db() as session:
            result = await session.execute(
                text(f"""
                    SELECT
                        id, file_path, content, language,
                        repo_id, line_start, line_end,
                        1 - (embedding <=> :query_embedding) as similarity
                    FROM ai.code_embeddings
                    WHERE {where_clause}
                      AND 1 - (embedding <=> :query_embedding) > :min_score
                    ORDER BY similarity DESC
                    LIMIT :top_k
                """),
                params,
            )
            rows = result.fetchall()

        ranked = []
        for row in rows:
            ranked.append({
                "file_path": row["file_path"],
                "content": row["content"],
                "language": row["language"],
                "repo_id": row["repo_id"],
                "score": float(row["similarity"]),
                "line_start": row["line_start"],
                "line_end": row["line_end"],
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]
