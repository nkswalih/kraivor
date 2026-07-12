from app.application.agents.prompts.specialist import EXPLAINER_SYSTEM_PROMPT
from app.application.provisioning.key_resolver import KeyResolver
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.router import ModelRouter


def _format_prompt(
    template: str, user_name: str | None, user_context: str | None
) -> str:
    name = user_name or "the user"
    ctx = f"Known context about the user:\n{user_context}" if user_context else ""
    return template.format(user_name=name, user_context=ctx)


class ExplainerNode:
    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()

    async def __call__(self, state: dict) -> dict:
        user_id = state.get("user_id", "")
        user_name = state.get("user_name")
        user_context = state.get("user_context")
        route = self.router.get_route("code_review")
        api_key, provider = await self.key_resolver.resolve(user_id, route["model"])
        client = LLMClient(api_key=api_key, provider=provider, model=route["model"])

        findings = []
        sections = {
            "code_findings": "Code Review Findings",
            "security_findings": "Security Findings",
            "architecture_findings": "Architecture Findings",
            "performance_findings": "Performance Findings",
        }

        for key, label in sections.items():
            vals = state.get(key)
            if vals:
                for v in vals:
                    findings.append(f"=== {label} ===\n{v}")

        context = state.get("assembled_context") or ""
        user_msg = state.get("message", "")
        history = state.get("context_history") or []
        tool_results = state.get("tool_results")

        parts = [f"Original query: {user_msg}"]

        if tool_results:
            parts.append(f"Workspace data:\n{tool_results}")

        if context:
            parts.append(f"Repository context:\n{context}")

        if findings:
            parts.append("Analysis findings:\n" + "\n\n".join(findings))

        if history:
            brief = "\n".join(
                f"{h.get('role', 'user')}: {h.get('content', '')[:200]}"
                for h in history[-5:]
            )
            parts.append(f"Recent conversation:\n{brief}")

        messages = [
            {
                "role": "system",
                "content": _format_prompt(
                    EXPLAINER_SYSTEM_PROMPT, user_name, user_context
                ),
            },
            {"role": "user", "content": "\n\n".join(parts)},
        ]

        response = await client.generate(messages, max_tokens=route["max_tokens"])

        return {"response": response["content"], "usage": response}
