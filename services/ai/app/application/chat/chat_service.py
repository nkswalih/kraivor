from collections.abc import AsyncGenerator
from app.core.config import settings
from app.application.agents.graph import build_agent_graph
from app.application.provisioning.key_resolver import KeyResolver
from app.application.chat.conversation_repository import (
    ensure_conversation,
    save_message,
    update_conversation_after_message,
)
from app.infrastructure.llm.router import ModelRouter
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.db.database import async_session_factory
from app.infrastructure.service_client import ServiceClient
from app.domain.entities.message import Message as MessageEntity, MessageRole


class ChatService:
    def __init__(self):
        client = ServiceClient(
            core_url=settings.core_api_url,
            analysis_url=settings.analysis_api_url,
        )
        self.graph = build_agent_graph(client=client)
        self.key_resolver = KeyResolver()
        self.router = ModelRouter()

    async def chat(self, user_id: str, message: str, conversation_id: str | None = None,
                   workspace_id: str | None = None, repo_ids: list[str] | None = None,
                   history: list[dict] | None = None, stream: bool = False,
                   model: str | None = None,
) -> dict:
        state = {
            "user_id": user_id,
            "workspace_id": workspace_id,
            "message": message,
            "conversation_id": conversation_id,
            "repo_ids": repo_ids,
            "model": model,
            "stream": stream,
            "intent": None,
            "complexity": None,
            "required_agents": None,
            "context_hints": [],
            "needs_rag": False,
            "needs_tools": False,
            "context_code": None,
            "context_analysis": None,
            "context_history": history or [],
            "assembled_context": None,
            "messages": [],
            "tool_results": None,
            "tool_calls": [],
            "sources": [],
            "code_findings": None,
            "security_findings": None,
            "architecture_findings": None,
            "performance_findings": None,
            "response": None,
            "usage": None,
        }

        result = await self.graph.ainvoke(state)
        response = result.get("response", "")
        usage = result.get("usage") or {}

        # Persist conversation and messages
        async with async_session_factory() as db:
            if conversation_id:
                conv = await ensure_conversation(
                    db, conversation_id, user_id, workspace_id or "", model
                )
                await save_message(db, MessageEntity(
                    role=MessageRole.USER,
                    content=message,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    model=model,
                ))
                if response:
                    assistant_msg = await save_message(db, MessageEntity(
                        role=MessageRole.ASSISTANT,
                        content=response,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        model=usage.get("model", model),
                        tokens_input=usage.get("input_tokens"),
                        tokens_output=usage.get("output_tokens"),
                        metadata=usage,
                    ))
                await update_conversation_after_message(
                    db,
                    conversation_id,
                    last_message_ts=assistant_msg.created_at if response else None,
                    title=message[:80],
                    model=usage.get("model", model),
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )
            await db.commit()

        return result

    async def stream_chat(self, user_id: str, message: str, **kwargs
) -> AsyncGenerator[dict, None]:
        result = await self.chat(user_id=user_id, message=message, **kwargs)
        content = result.get('response', '')
        title = None
        conv_id = kwargs.get("conversation_id")
        if conv_id:
            from sqlalchemy import select
            from app.infrastructure.db.models.conversation import Conversation
            async with async_session_factory() as db:
                conv_result = await db.execute(
                    select(Conversation).where(Conversation.id == conv_id)
                )
                conv = conv_result.scalar_one_or_none()
                if conv:
                    title = conv.title

        yield {"content": content}
        yield {"done": True, "conversation_id": conv_id, "title": title}
