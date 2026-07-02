import json
import logging
from app.application.agents.prompts.orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    RESPOND_DIRECT_PROMPT,
    CODE_GENERATION_PROMPT,
    WRITING_PROMPT,
)
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.router import ModelRouter
from app.application.provisioning.key_resolver import KeyResolver

logger = logging.getLogger(__name__)

DIRECT_INTENTS = {
    "greeting", "conversation", "question", "programming",
    "code_generation", "writing", "translation", "planning",
    "unknown",
}

_INTENT_PROMPT_MAP = {
    "code_generation": CODE_GENERATION_PROMPT,
    "documentation": CODE_GENERATION_PROMPT,
    "writing": WRITING_PROMPT,
}

_INTENT_ROUTE_MAP = {
    "code_generation": "code_generation",
    "documentation": "code_generation",
    "writing": "code_generation",
}


class OrchestratorNode:
    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()

    async def __call__(self, state: dict) -> dict:
        user_id = state.get("user_id", "")
        message = state.get("message", "")
        stream = state.get("stream", False)
        route = self.router.get_route("intent_classify")
        history = state.get("context_history") or []

        api_key, provider = await self.key_resolver.resolve(user_id, route["model"])
        client = LLMClient(api_key=api_key, provider=provider, model=route["model"])

        response = await client.generate([
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": message},
        ], max_tokens=route["max_tokens"], response_format={"type": "json_object"})

        try:
            analysis = json.loads(response["content"])
        except (json.JSONDecodeError, KeyError):
            analysis = {
                "intent": "conversation",
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

        # Route to tool executor for workspace queries that need live data
        if needs_tools or (intent == "workspace_query"):
            return {
                "intent": intent,
                "complexity": analysis.get("complexity", "simple"),
                "required_agents": analysis.get("required_agents", []),
                "context_hints": analysis.get("context_hints", []),
                "needs_rag": False,
                "needs_tools": True,
                "response": None,
            }

        # For direct-response intents that don't need context, generate immediately
        if intent in DIRECT_INTENTS and not needs_context and not needs_rag:
            intent_prompt = _INTENT_PROMPT_MAP.get(intent, RESPOND_DIRECT_PROMPT)
            intent_route_name = _INTENT_ROUTE_MAP.get(intent, "simple_qa")
            respond_route = self.router.get_route(intent_route_name)
            api_key, provider = await self.key_resolver.resolve(user_id, respond_route["model"])
            respond_client = LLMClient(api_key=api_key, provider=provider, model=respond_route["model"])

            messages = []
            for h in history[-10:]:
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
            messages.append({"role": "system", "content": intent_prompt})
            messages.append({"role": "user", "content": message})

            result = await respond_client.generate(
                messages, max_tokens=respond_route["max_tokens"]
            )

            return {
                "intent": intent,
                "complexity": analysis.get("complexity", "simple"),
                "response": result["content"],
                "usage": result,
                "required_agents": [],
                "context_hints": [],
            }

        return {
            "intent": intent,
            "complexity": analysis.get("complexity", "simple"),
            "required_agents": analysis.get("required_agents", []),
            "context_hints": analysis.get("context_hints", []),
            "needs_rag": needs_rag,
            "needs_tools": needs_tools,
            "response": None,
        }
