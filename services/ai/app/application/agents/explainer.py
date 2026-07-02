from app.application.agents.prompts.specialist import EXPLAINER_SYSTEM_PROMPT
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.router import ModelRouter
from app.application.provisioning.key_resolver import KeyResolver


class ExplainerNode:
    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()

    async def __call__(self, state: dict) -> dict:
        user_id = state.get("user_id", "")
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
            parts.append(f"Analysis findings:\n" + "\n\n".join(findings))

        if history:
            brief = "\n".join(
                f"{h.get('role', 'user')}: {h.get('content', '')[:200]}"
                for h in history[-5:]
            )
            parts.append(f"Recent conversation:\n{brief}")

        messages = [
            {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
            {"role": "user", "content": "\n\n".join(parts)},
        ]

        response = await client.generate(messages, max_tokens=route["max_tokens"])

        return {"response": response["content"], "usage": response}
