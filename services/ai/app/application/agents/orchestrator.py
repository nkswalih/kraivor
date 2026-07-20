import json
import hashlib
import re

import logging

from app.application.agents.prompts.orchestrator import (
    CODE_GENERATION_PROMPT,
    GREETING_PROMPT,
    ORCHESTRATOR_SYSTEM_PROMPT,
    RESPOND_DIRECT_PROMPT,
    WRITING_PROMPT,
)
from app.application.provisioning.key_resolver import KeyResolver
from app.infrastructure.llm.client import LLMClient, LLM_SHORT_TIMEOUT
from app.infrastructure.llm.router import ModelRouter

logger = logging.getLogger(__name__)

INTENT_CACHE_TTL = 300  # 5 minutes

# Fix A: Regex to detect obvious greetings — bypasses intent classification LLM call entirely.
# Saves 1-2 seconds per greeting. Pattern matches: hi, hy, hello, hey, yo, sup, greetings,
# good morning/afternoon/evening, what's up, how are you, etc.
_GREETING_RE = re.compile(
    r"^(hi|hy|hello|hey|yo|sup|greetings|howdy|hola|"
    r"good\s+(morning|afternoon|evening|day)|"
    r"what'?s\s+up|how\s+are\s+you|how(?:'s| is) it going|"
    r"how(?:'s| is) everything|what'?s\s+new|howdy|"
    r"hiya|heya|wassup|whassup|howdydo|r'you good|"
    r"you good|hey there|hello there|hi there|"
    r"gm|gn|morning|evening|afternoon)"
    r"[\s!?.]*$",
    re.IGNORECASE,
)

_DIRECT_INTENTS = {
    "greeting",
    "conversation",
    "unknown",
}

_EVIDENCE_INTENTS = {
    "question",
    "programming",
    "documentation",
    "planning",
    "translation",
    "devops",
    "security_audit",
    "data_science",
    "cloud_engineering",
    "system_design",
    "ui_ux",
    "database_design",
    "testing",
    "full_stack",
    "code_generation",
    "writing",
}

_NEWS_KEYWORDS = {
    "news", "breaking", "today", "latest news", "recent news",
    "current events", "what happened", "headlines", "daily news",
    "tech news", "technology news", "world news", "global news",
    "morning briefing", "daily briefing", "news compilation",
    "what's going on", "what's happening",
}

_INTENT_PROMPT_MAP = {
    "greeting": GREETING_PROMPT,
    "code_generation": CODE_GENERATION_PROMPT,
    "documentation": CODE_GENERATION_PROMPT,
    "writing": WRITING_PROMPT,
}

_INTENT_ROUTE_MAP = {
    "code_generation": "code_generation",
    "documentation": "code_generation",
    "writing": "code_generation",
}


def _format_prompt(
    template: str, user_name: str | None, user_context: str | None
) -> str:
    name = user_name or "the user"
    ctx = f"Known context about the user:\n{user_context}" if user_context else ""
    return template.format(user_name=name, user_context=ctx)


class OrchestratorNode:
    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()

    async def __call__(self, state: dict) -> dict:
        user_id = state.get("user_id", "")
        user_name = state.get("user_name")
        user_context = state.get("user_context")
        message = state.get("message", "")
        user_model = state.get("model")
        history = state.get("context_history") or []

        # Fix A: Bypass intent classification for obvious greetings.
        # Saves 1-2 seconds by skipping the intent LLM call entirely.
        if _GREETING_RE.match(message.strip()):
            logger.info("Greeting detected via regex, bypassing intent classification")
            intent_prompt = _format_prompt(GREETING_PROMPT, user_name, user_context)
            greet_route = self.router.get_route_for_user("simple_qa", user_model)
            api_key, provider = await self.key_resolver.resolve(user_id, greet_route["model"])
            greet_client = LLMClient(api_key=api_key, provider=provider, model=greet_route["model"])
            greet_msgs = [{"role": "user", "content": message}]
            greet_result = await greet_client.generate(greet_msgs, max_tokens=greet_route["max_tokens"])
            return {
                "intent": "greeting",
                "complexity": "simple",
                "response": greet_result["content"],
                "usage": greet_result,
                "required_agents": [],
                "context_hints": [],
                "needs_evidence": False,
            }

        history_hash = hashlib.sha256(
            "|".join(h.get("content", "")[:100] for h in history[-3:]).encode()
        ).hexdigest()[:16]
        intent_cache_key = f"intent:{user_id}:{hashlib.sha256(f'{message}:{history_hash}'.encode()).hexdigest()[:24]}"

        try:
            from app.infrastructure.cache.redis_client import get_redis
            r = await get_redis()
            cached = await r.get(intent_cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        route = self.router.get_route_for_user("intent_classify", user_model)

        api_key, provider = await self.key_resolver.resolve(user_id, route["model"])
        client = LLMClient(api_key=api_key, provider=provider, model=route["model"])

        gen_kwargs = {
            "max_tokens": route["max_tokens"],
        }
        # Use json_object format for providers that support it
        if provider in ("openai", "groq"):
            gen_kwargs["response_format"] = {"type": "json_object"}

        # Build intent classification messages — include recent history so the
        # classifier understands context (e.g. "continue" after a long answer).
        classify_msgs = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
        ]
        if history:
            for h in history[-8:]:
                classify_msgs.append(
                    {"role": h.get("role", "user"), "content": h.get("content", "")[:600]}
                )
        classify_msgs.append({"role": "user", "content": message})

        response = await client.generate(classify_msgs, timeout=LLM_SHORT_TIMEOUT, **gen_kwargs)

        try:
            analysis = json.loads(response["content"])
        except (json.JSONDecodeError, KeyError):
            analysis = {
                "intent": "question",
                "complexity": "simple",
                "needs_context": False,
                "needs_rag": False,
                "context_hints": [],
                "required_agents": [],
            }

        intent = analysis.get("intent", "conversation")
        needs_context = analysis.get("needs_context", False)
        needs_rag = analysis.get("needs_rag", False)
        needs_tools = analysis.get("needs_tools", False)

        # Route to tool executor for workspace queries that need live data.
        # But if the intent is a knowledge question, prioritize evidence gathering
        # over tool execution — workspace tools can't answer "what is Kraivor?"
        is_workspace_query = needs_tools and intent not in _EVIDENCE_INTENTS
        if is_workspace_query or (intent == "workspace_query"):
            result = {
                "intent": intent,
                "complexity": analysis.get("complexity", "simple"),
                "required_agents": analysis.get("required_agents", []),
                "context_hints": analysis.get("context_hints", []),
                "needs_rag": False,
                "needs_tools": True,
                "needs_evidence": False,
                "response": None,
            }
            try:
                from app.infrastructure.cache.redis_client import get_redis
                r = await get_redis()
                await r.setex(intent_cache_key, INTENT_CACHE_TTL, json.dumps(result))
            except Exception:
                pass
            return result

        # News/current-events queries: route to tool_executor for web_search_news
        # instead of evidence_gatherer which uses generic DDGS (returns forums)
        msg_lower = message.lower()
        is_news_query = any(kw in msg_lower for kw in _NEWS_KEYWORDS)
        if is_news_query and intent in _EVIDENCE_INTENTS:
            result = {
                "intent": intent,
                "complexity": analysis.get("complexity", "simple"),
                "required_agents": [],
                "context_hints": analysis.get("context_hints", []),
                "needs_rag": False,
                "needs_tools": True,
                "needs_evidence": False,
                "response": None,
            }
            try:
                from app.infrastructure.cache.redis_client import get_redis
                r = await get_redis()
                await r.setex(intent_cache_key, INTENT_CACHE_TTL, json.dumps(result))
            except Exception:
                pass
            return result

        # For direct-response intents (greeting, casual chat), generate immediately
        if intent in _DIRECT_INTENTS and not needs_context and not needs_rag:
            intent_prompt = _INTENT_PROMPT_MAP.get(intent, RESPOND_DIRECT_PROMPT)
            intent_prompt = _format_prompt(intent_prompt, user_name, user_context)
            intent_route_name = _INTENT_ROUTE_MAP.get(intent, "simple_qa")
            respond_route = self.router.get_route_for_user(intent_route_name, user_model)
            api_key, provider = await self.key_resolver.resolve(
                user_id, respond_route["model"]
            )
            respond_client = LLMClient(
                api_key=api_key, provider=provider, model=respond_route["model"]
            )

            messages = []
            for h in history[-15:]:
                messages.append(
                    {"role": h.get("role", "user"), "content": h.get("content", "")[:1000]}
                )
            messages.append({"role": "system", "content": intent_prompt})
            messages.append({"role": "user", "content": message})

            result = await respond_client.generate(
                messages, max_tokens=respond_route["max_tokens"]
            )

            response = {
                "intent": intent,
                "complexity": analysis.get("complexity", "simple"),
                "response": result["content"],
                "usage": result,
                "required_agents": [],
                "context_hints": [],
                "needs_evidence": False,
            }
            try:
                from app.infrastructure.cache.redis_client import get_redis
                r = await get_redis()
                await r.setex(intent_cache_key, INTENT_CACHE_TTL, json.dumps(response))
            except Exception:
                pass
            return response

        # For evidence-gathering intents, route through the knowledge pipeline
        if intent in _EVIDENCE_INTENTS:
            result = {
                "intent": intent,
                "complexity": analysis.get("complexity", "simple"),
                "required_agents": analysis.get("required_agents", []),
                "context_hints": analysis.get("context_hints", []),
                "needs_rag": needs_rag,
                "needs_tools": False,
                "needs_evidence": True,
                "response": None,
            }
            try:
                from app.infrastructure.cache.redis_client import get_redis
                r = await get_redis()
                await r.setex(intent_cache_key, INTENT_CACHE_TTL, json.dumps(result))
            except Exception:
                pass
            return result

        result = {
            "intent": intent,
            "complexity": analysis.get("complexity", "simple"),
            "required_agents": analysis.get("required_agents", []),
            "context_hints": analysis.get("context_hints", []),
            "needs_rag": needs_rag,
            "needs_tools": needs_tools,
            "needs_evidence": False,
            "response": None,
        }
        try:
            from app.infrastructure.cache.redis_client import get_redis
            r = await get_redis()
            await r.setex(intent_cache_key, INTENT_CACHE_TTL, json.dumps(result))
        except Exception:
            pass
        return result
