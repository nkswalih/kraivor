from app.application.tools.base import BaseTool
from app.infrastructure.rag.retriever import Retriever


class CodeSearchTool(BaseTool):
    name = "code_search"
    description = "Search indexed codebase by semantic similarity"

    def __init__(self, retriever: Retriever | None = None):
        self.retriever = retriever

    async def run(self, query: str, repo_ids: list[str] | None = None,
                  workspace_id: str | None = None, top_k: int = 5) -> str:
        if not self.retriever or self.retriever.db is None:
            return "Code search unavailable (no database connection)."
        results = await self.retriever.retrieve(
            query=query,
            repo_ids=repo_ids,
            workspace_id=workspace_id,
            top_k=top_k,
        )
        if not results:
            return "No matching code found."
        return "\n\n".join(
            f"**{r['file_path']}:{r['line_start']}-{r['line_end']}** "
            f"(score: {r['score']:.3f})\n```\n{r['content']}\n```"
            for r in results
        )
