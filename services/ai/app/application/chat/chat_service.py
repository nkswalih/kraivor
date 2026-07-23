from collections.abc import AsyncGenerator

import json
import logging
from datetime import datetime, timezone

from app.application.agents.graph import build_agent_graph
from app.application.chat.conversation_repository import (
    ensure_conversation,
    get_messages,
    save_message,
    update_conversation_after_message,
)
from app.application.memory.user_memory_service import (
    extract_and_store_facts,
    get_user_context,
)
from app.application.provisioning.key_resolver import KeyResolver
from app.core.config import settings
from app.core.exceptions import AllProvidersFailedError
from app.domain.entities.message import Message as MessageEntity
from app.domain.entities.message import MessageRole
from app.infrastructure.cache.query_cache import SemanticQueryCache
from app.application.usage.usage_service import increment_daily_usage
from app.infrastructure.db.database import async_session_factory
from app.infrastructure.llm.error_classifier import ClassifiedError, ErrorCategory
from app.infrastructure.llm.failover_engine import FailoverEngine
from app.infrastructure.llm.router import ModelRouter
from app.infrastructure.service_client import ServiceClient

logger = logging.getLogger(__name__)


def _format_error_for_user(error: ClassifiedError | AllProvidersFailedError) -> dict:
    """Build a user-friendly error response with actionable details."""
    if isinstance(error, AllProvidersFailedError):
        return {
            "response": (
                "All AI providers are currently unavailable. This is usually due to "
                "exceeded credits or rate limits.\n\n"
                "**What you can do:**\n"
                "- Add your own API key in Settings (BYOK)\n"
                "- Switch to a different model\n"
                "- Try again in a few minutes"
            ),
            "provider_error": True,
            "error_details": {
                "category": "all_providers_failed",
                "tried_providers": error.tried_providers,
                "suggested_action": "add_key",
            },
        }
    return {
        "response": error.user_message,
        "provider_error": True,
        "error_details": {
            "category": error.category.value,
            "provider": error.provider,
            "suggested_action": error.suggested_action.value,
            "retry_after": error.retry_after,
        },
    }
_HISTORY_LIMIT = 30
_HISTORY_CACHE_TTL = 300  # 5 minutes (was 60s — almost always a cache miss at 60s)


def _current_date_block() -> str:
    """Return a date context block prepended to every system prompt."""
    now = datetime.now(timezone.utc)
    return (
        f"CURRENT DATE & TIME: {now.strftime('%A, %B %d, %Y — %H:%M UTC')}\n"
        "This is the real current date from the server. Use this as your time reference. "
        "NEVER state a different date or year unless explicitly told otherwise."
    )


class ChatService:
    def __init__(self):
        client = ServiceClient(
            core_url=settings.core_api_url, analysis_url=settings.analysis_api_url
        )
        self.graph = build_agent_graph(client=client)
        self.key_resolver = KeyResolver()
        self.router = ModelRouter()
        self.query_cache = SemanticQueryCache()
        self.failover = FailoverEngine(self.key_resolver)

    async def _load_history(self, conversation_id: str) -> list[dict]:
        """Load the last N messages from the database for context."""
        try:
            from app.infrastructure.cache.redis_client import get_redis
            import json
            r = await get_redis()
            cached = await r.get(f"history:{conversation_id}")
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        async with async_session_factory() as db:
            messages = await get_messages(db, conversation_id, limit=_HISTORY_LIMIT)
        history = [
            {"role": m.role.value, "content": m.content}
            for m in messages
            if m.role in (MessageRole.USER, MessageRole.ASSISTANT)
        ]

        try:
            from app.infrastructure.cache.redis_client import get_redis
            import json
            r = await get_redis()
            await r.setex(f"history:{conversation_id}", _HISTORY_CACHE_TTL, json.dumps(history))
        except Exception:
            pass

        return history

    async def _invalidate_history_cache(self, conversation_id: str) -> None:
        try:
            from app.infrastructure.cache.redis_client import get_redis
            r = await get_redis()
            await r.delete(f"history:{conversation_id}")
        except Exception:
            pass

    async def chat(
        self,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        workspace_id: str | None = None,
        repo_ids: list[str] | None = None,
        history: list[dict] | None = None,
        stream: bool = False,
        model: str | None = None,
        user_name: str | None = None,
    ) -> dict:
        # Load conversation history from DB if we have a conversation_id
        if conversation_id and not history:
            db_history = await self._load_history(conversation_id)
        else:
            db_history = history or []

        # Simple truncation: keep last N turns to stay within token budgets
        if len(db_history) > _HISTORY_LIMIT:
            db_history = db_history[-_HISTORY_LIMIT:]

        # Load cross-session user memory
        async with async_session_factory() as db:
            user_context_str = await get_user_context(db, user_id)
        user_context_str = user_context_str or None

        state = {
            "user_id": user_id,
            "user_name": user_name,
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
            "needs_evidence": False,
            "context_code": None,
            "context_analysis": None,
            "context_history": db_history,
            "assembled_context": None,
            "user_context": user_context_str,
            "messages": [],
            "tool_results": None,
            "tool_calls": [],
            "sources": [],
            "evidence": None,
            "evidence_sources": [],
            "code_findings": None,
            "security_findings": None,
            "architecture_findings": None,
            "performance_findings": None,
            "low_confidence": False,
            "parallel": False,
            "response": None,
            "usage": None,
        }

        # Note: Project doc seeding is handled by EvidenceGathererNode on-the-fly
        # so docs are guaranteed to exist before evidence retrieval runs.

        try:
            result = await self.graph.ainvoke(state)
        except ClassifiedError as e:
            logger.warning("provider_error graph_invoke category=%s", e.category.value)
            result = _format_error_for_user(e)
        except AllProvidersFailedError as e:
            logger.error("all_providers_failed tried=%s", e.tried_providers)
            result = _format_error_for_user(e)
        response = result.get("response", "")
        usage = result.get("usage") or {}

        # Persist conversation and messages
        async with async_session_factory() as db:
            if conversation_id:
                await ensure_conversation(
                    db, conversation_id, user_id, workspace_id or "", model
                )
                await save_message(
                    db,
                    MessageEntity(
                        role=MessageRole.USER,
                        content=message,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        model=model,
                    ),
                )
                if response:
                    assistant_msg = await save_message(
                        db,
                        MessageEntity(
                            role=MessageRole.ASSISTANT,
                            content=response,
                            conversation_id=conversation_id,
                            user_id=user_id,
                            model=usage.get("model", model),
                            tokens_input=usage.get("input_tokens"),
                            tokens_output=usage.get("output_tokens"),
                            metadata=usage,
                        ),
                    )
                await update_conversation_after_message(
                    db,
                    conversation_id,
                    last_message_ts=assistant_msg.created_at if response else None,
                    title=message[:80],
                    model=usage.get("model", model),
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )

                # Extract and store user facts for cross-session memory
                try:
                    await extract_and_store_facts(db, user_id, message, conversation_id)
                except Exception as e:
                    logger.warning("Failed to extract user facts: %s", e)

                # Invalidate history cache after new messages are saved
                await self._invalidate_history_cache(conversation_id)

                # Extract and store conversation knowledge (background)
                try:
                    from app.application.tasks.knowledge import extract_conversation_knowledge
                    messages_for_extraction = [
                        {"role": m.get("role", "user"), "content": m.get("content", "")}
                        for m in db_history[-10:]
                    ]
                    if messages_for_extraction:
                        extract_conversation_knowledge.delay(
                            workspace_id=workspace_id or "",
                            conversation_id=conversation_id,
                            messages=messages_for_extraction,
                        )
                except Exception as e:
                    logger.debug("Failed to queue conversation knowledge extraction: %s", e)

            await db.commit()

        return result

    async def stream_chat(
        self, user_id: str, message: str, **kwargs
    ) -> AsyncGenerator[dict, None]:
        """True token-by-token streaming via LLM client.stream().

        Strategy:
        1. Run the graph (orchestrator → tools → context → analysts → explainer)
           to get all state: context, tool_results, findings, etc.
        2. Build the explainer prompt from the final state.
        3. Stream the response token-by-token using the LLM client.
        4. Persist the full response after streaming completes.
        """
        conversation_id = kwargs.get("conversation_id")
        workspace_id = kwargs.get("workspace_id")
        model = kwargs.get("model")
        user_name = kwargs.get("user_name")

        # Load conversation history
        if conversation_id:
            db_history = await self._load_history(conversation_id)
        else:
            db_history = kwargs.get("history") or []

        # Simple truncation: keep last N turns to stay within token budgets
        if len(db_history) > _HISTORY_LIMIT:
            db_history = db_history[-_HISTORY_LIMIT:]

        # Load user context
        async with async_session_factory() as db:
            user_context_str = await get_user_context(db, user_id)
        user_context_str = user_context_str or None

        # Check semantic query cache — skip full pipeline if a similar query was recently answered
        model_key = model or ""
        try:
            cached_response = await self.query_cache.get(message, model_key)
            if cached_response:
                logger.info("query_cache: hit for message='%s'", message[:50])
                import asyncio
                chunk_size = 20
                for i in range(0, len(cached_response), chunk_size):
                    yield {"content": cached_response[i : i + chunk_size]}
                    await asyncio.sleep(0.03)
                yield {"done": True, "conversation_id": conversation_id, "title": None, "usage": {}}
                await self._persist_streaming_response(
                    user_id, message, cached_response, conversation_id, workspace_id, model, {}
                )
                return
        except Exception as e:
            logger.debug("query_cache lookup failed: %s", e)

        # Build initial state
        state = {
            "user_id": user_id,
            "user_name": user_name,
            "workspace_id": workspace_id,
            "message": message,
            "conversation_id": conversation_id,
            "repo_ids": kwargs.get("repo_ids"),
            "model": model,
            "stream": True,
            "intent": None,
            "complexity": None,
            "required_agents": None,
            "context_hints": [],
            "needs_rag": False,
            "needs_tools": False,
            "needs_evidence": False,
            "context_code": None,
            "context_analysis": None,
            "context_history": db_history,
            "assembled_context": None,
            "user_context": user_context_str,
            "messages": [],
            "tool_results": None,
            "tool_calls": [],
            "sources": [],
            "evidence": None,
            "evidence_sources": [],
            "code_findings": None,
            "security_findings": None,
            "architecture_findings": None,
            "performance_findings": None,
            "low_confidence": False,
            "parallel": False,
            "response": None,
            "usage": None,
        }

        # Run graph to get context/tool results
        yield {"status": "Planning solution"}
        try:
            result = await self.graph.ainvoke(state)
        except ClassifiedError as e:
            logger.warning("provider_error stream_graph category=%s", e.category.value)
            yield {"type": "error", "error": e.user_message, "category": e.category.value,
                   "suggested_action": e.suggested_action.value, "provider": e.provider}
            return
        except AllProvidersFailedError as e:
            logger.error("all_providers_failed stream_graph tried=%s", e.tried_providers)
            yield {"type": "error", "error": "All AI providers are exhausted.",
                   "category": "all_providers_failed", "suggested_action": "add_key"}
            return

        # If graph already produced a response (via tool_executor or explainer), stream it
        if result.get("response"):
            full_response = result["response"]
            usage = result.get("usage") or {}
            import asyncio
            chunk_size = 20
            for i in range(0, len(full_response), chunk_size):
                yield {"content": full_response[i : i + chunk_size]}
                await asyncio.sleep(0.03)
            yield {"done": True, "conversation_id": conversation_id, "title": None, "usage": usage}
            await self._persist_streaming_response(
                user_id, message, full_response, conversation_id, workspace_id, model, usage
            )
            # Track daily token usage
            try:
                await increment_daily_usage(
                    user_id,
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                )
            except Exception as e:
                logger.debug("daily_usage_increment failed: %s", e)
            # Cache the response for similar future queries (skip very short responses)
            if len(full_response) > 50:
                try:
                    await self.query_cache.set(message, model_key, full_response)
                except Exception as e:
                    logger.debug("query_cache set failed: %s", e)
            return

        # Fallback: graph didn't produce a response (shouldn't happen in normal flow)
        # Stream a simple error message rather than making a duplicate LLM call.
        yield {"content": "I wasn't able to generate a response. Please try again."}
        yield {"done": True, "conversation_id": conversation_id, "title": None, "usage": {}}

    async def _persist_streaming_response(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        conversation_id: str | None,
        workspace_id: str | None,
        model: str | None,
        usage: dict,
    ) -> None:
        """Persist conversation and messages after streaming completes."""
        if not conversation_id:
            return

        try:
            async with async_session_factory() as db:
                await ensure_conversation(
                    db, conversation_id, user_id, workspace_id or "", model
                )
                await save_message(
                    db,
                    MessageEntity(
                        role=MessageRole.USER,
                        content=user_message,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        model=model,
                    ),
                )
                if assistant_response:
                    assistant_msg = await save_message(
                        db,
                        MessageEntity(
                            role=MessageRole.ASSISTANT,
                            content=assistant_response,
                            conversation_id=conversation_id,
                            user_id=user_id,
                            model=usage.get("model", model),
                            tokens_input=usage.get("input_tokens"),
                            tokens_output=usage.get("output_tokens"),
                            metadata=usage,
                        ),
                    )
                    await update_conversation_after_message(
                        db,
                        conversation_id,
                        last_message_ts=assistant_msg.created_at,
                        title=user_message[:80],
                        model=usage.get("model", model),
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                    )

                # Extract user facts (non-blocking)
                try:
                    await extract_and_store_facts(db, user_id, user_message, conversation_id)
                except Exception as e:
                    logger.warning("Failed to extract user facts: %s", e)

                await db.commit()

                # Invalidate history cache after new messages are saved
                await self._invalidate_history_cache(conversation_id)
        except Exception as e:
            logger.error("Failed to persist streaming response: %s", e)
