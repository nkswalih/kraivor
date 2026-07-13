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

    async def _retrieve_knowledge(self, query: str, workspace_id: str) -> str:
        """Retrieve relevant knowledge from the persistent knowledge base."""
        if not workspace_id:
            return ""
        try:
            from app.knowledge_engine.store.knowledge_retriever import KnowledgeRetriever
            kr = KnowledgeRetriever()
            results = await kr.retrieve(workspace_id=workspace_id, query=query, top_k=5)
            if not results:
                return ""
            parts = []
            for item in results:
                score = item.get("similarity", 0)
                title = item.get("title", "Untitled")
                provider = item.get("provider", "")
                content = item.get("content", "")[:1500]
                parts.append(f"[{title}] ({provider}, relevance: {score:.2f})\n{content}")
            return "\n\n".join(parts)
        except Exception as e:
            logger.debug("Knowledge retrieval failed: %s", e)
            return ""

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

        # Retrieve stored knowledge for context
        knowledge_context = ""
        query_text = ". ".join(filter(None, [message, *hints]))
        if query_text and workspace_id:
            knowledge_context = await self._retrieve_knowledge(query_text, workspace_id)

        # Assemble all context sources
        sections = []
        if results:
            sections.append(f"# Code Context\n\n{results}")
        if knowledge_context:
            sections.append(f"# Knowledge Base Context\n\n{knowledge_context}")
        if history:
            formatted = "\n".join(
                f"{'User' if h.get('role') == 'user' else 'Assistant'}: {h.get('content', '')[:500]}"
                for h in history[-15:]
            )
            sections.append(f"# Conversation History\n\n{formatted}")

        assembled = "\n\n".join(sections) if sections else ""
        return {"assembled_context": assembled, "context_code": results}
