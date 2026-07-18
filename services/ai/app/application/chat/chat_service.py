from collections.abc import AsyncGenerator

import json
import logging

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
from app.domain.entities.message import Message as MessageEntity
from app.domain.entities.message import MessageRole
from app.infrastructure.db.database import async_session_factory
from app.infrastructure.llm.router import ModelRouter
from app.infrastructure.service_client import ServiceClient

logger = logging.getLogger(__name__)
_HISTORY_LIMIT = 30
_HISTORY_CACHE_TTL = 300  # 5 minutes (was 60s — almost always a cache miss at 60s)


class ChatService:
    def __init__(self):
        client = ServiceClient(
            core_url=settings.core_api_url, analysis_url=settings.analysis_api_url
        )
        self.graph = build_agent_graph(client=client)
        self.key_resolver = KeyResolver()
        self.router = ModelRouter()

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
            "response": None,
            "usage": None,
        }

        # Note: Project doc seeding is handled by EvidenceGathererNode on-the-fly
        # so docs are guaranteed to exist before evidence retrieval runs.

        result = await self.graph.ainvoke(state)
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

        # Load user context
        async with async_session_factory() as db:
            user_context_str = await get_user_context(db, user_id)
        user_context_str = user_context_str or None

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
            "response": None,
            "usage": None,
        }

        # Run graph to get context/tool results
        yield {"status": "Planning solution"}
        result = await self.graph.ainvoke(state)

        # If orchestrator or tool_executor already generated a direct response, stream it
        # Fix D: Include tool_executor responses (has tool_results + response) — skip explainer
        if result.get("response") and not result.get("assembled_context") and not result.get("evidence"):
            full_response = result["response"]
            usage = result.get("usage") or {}
            import asyncio
            chunk_size = 20
            for i in range(0, len(full_response), chunk_size):
                yield {"content": full_response[i : i + chunk_size]}
                await asyncio.sleep(0.03)
            yield {"done": True, "conversation_id": conversation_id, "title": None}
            await self._persist_streaming_response(
                user_id, message, full_response, conversation_id, workspace_id, model, usage
            )
            return

        # Build explainer prompt from graph state using intent-aware selection
        from app.application.agents.prompts.specialist import (
            EXPLAINER_SYSTEM_PROMPT,
            EXPLAINER_EVIDENCE_PROMPT,
            EXPLAINER_CASUAL_PROMPT,
            EXPLAINER_CODE_AUDIT_PROMPT,
            EXPLAINER_GENERAL_QA_PROMPT,
        )

        intent = result.get("intent")
        evidence = result.get("evidence")
        evidence_sources = result.get("evidence_sources") or []

        # Emit status based on what the graph decided to do
        if result.get("needs_tools"):
            yield {"status": "Inspecting project"}
        elif result.get("needs_evidence"):
            yield {"status": "Searching knowledge base"}

        findings = []
        sections = {
            "code_findings": "Code Review Findings",
            "security_findings": "Security Findings",
            "architecture_findings": "Architecture Findings",
            "performance_findings": "Performance Findings",
        }
        for key, label in sections.items():
            vals = result.get(key)
            if vals:
                for v in vals:
                    findings.append(f"=== {label} ===\n{v}")

        context = result.get("assembled_context") or ""
        tool_results = result.get("tool_results")

        has_findings = bool(findings)
        has_evidence = bool(evidence)
        has_user_context = bool(user_context_str)

        # Emit status based on what data we gathered
        if has_findings:
            yield {"status": "Analyzing code"}
        elif has_evidence:
            yield {"status": "Reviewing documentation"}
        else:
            yield {"status": "Finalizing response"}

        # Select prompt based on intent + available data
        _AUDIT_INTENTS = {"repository_analysis", "security_analysis", "architecture_review", "performance_analysis"}
        _CASUAL_INTENTS = {"greeting", "conversation"}

        if intent in _CASUAL_INTENTS:
            prompt_template = EXPLAINER_CASUAL_PROMPT
        elif intent in _AUDIT_INTENTS and has_findings:
            prompt_template = EXPLAINER_CODE_AUDIT_PROMPT
        elif has_evidence:
            prompt_template = EXPLAINER_EVIDENCE_PROMPT
        elif has_user_context:
            prompt_template = EXPLAINER_GENERAL_QA_PROMPT
        else:
            prompt_template = EXPLAINER_SYSTEM_PROMPT

        # Build user message — user context FIRST as primary knowledge source
        parts = []

        if user_context_str:
            parts.append(f"## What you know about this user and their projects\n{user_context_str}")

        parts.append(f"## User's question\n{message}")

        if evidence:
            parts.append(f"## Verified research sources\n{evidence}")
        if tool_results:
            parts.append(f"## Workspace data\n{tool_results}")
        if context:
            parts.append(f"## Repository context\n{context}")
        if findings:
            parts.append("## Analysis findings\n" + "\n\n".join(findings))
        if db_history:
            brief = "\n".join(
                f"{'User' if h.get('role') == 'user' else 'Assistant'}: {h.get('content', '')[:500]}"
                for h in db_history[-15:]
            )
            parts.append(f"## Recent conversation\n{brief}")

        # Format system prompt with user context
        name = user_name or "the user"
        ctx = f"Known context about the user:\n{user_context_str}" if user_context_str else ""
        system_prompt = prompt_template.format(user_name=name, user_context=ctx)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n\n".join(parts)},
        ]

        # Resolve LLM key and create streaming client
        route = self.router.get_route_for_user("code_review", model)
        api_key, provider = await self.key_resolver.resolve(user_id, route["model"])
        from app.infrastructure.llm.client import LLMClient
        client = LLMClient(api_key=api_key, provider=provider, model=route["model"])

        yield {"status": "Writing response"}

        # Stream token-by-token
        full_response = ""
        async for token in client.stream(messages, max_tokens=route["max_tokens"]):
            full_response += token
            yield {"content": token}

        yield {"done": True, "conversation_id": conversation_id, "title": None}

        # Persist the complete response
        usage = {"model": route["model"], "provider": provider, "input_tokens": 0, "output_tokens": 0}
        await self._persist_streaming_response(
            user_id, message, full_response, conversation_id, workspace_id, model, usage
        )

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
