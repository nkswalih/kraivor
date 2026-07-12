import logging

from app.infrastructure.rag.embedder import Embedder
from app.infrastructure.rag.retriever import Retriever

logger = logging.getLogger(__name__)


class ContextAssemblerNode:
    def __init__(self, retriever: Retriever | None = None):
        self.retriever = retriever
        if retriever is None:
            try:
                self.retriever = Retriever(embedder=Embedder(), db_session_factory=None)
            except Exception as e:
                logger.warning("Failed to init Retriever: %s", e)

    async def __call__(self, state: dict) -> dict:
        needs_rag = state.get("needs_rag", False)
        repo_ids = state.get("repo_ids")
        workspace_id = state.get("workspace_id")
        message = state.get("message", "")
        hints = state.get("context_hints") or []
        history = state.get("context_history") or []

        results = []
        if needs_rag and self.retriever and self.retriever.db is not None and repo_ids:
            query = ". ".join(filter(None, [message, *hints]))
            try:
                results = await self.retriever.retrieve(
                    query=query, repo_ids=repo_ids, workspace_id=workspace_id
                )
            except Exception as e:
                logger.error("RAG retrieval failed: %s", e)

        assembled = (
            f"# Code Context\n\n{results}\n\n# Conversation History\n\n{history}"
            if results
            else ""
        )
        return {"assembled_context": assembled, "context_code": results}
