from app.application.agents.prompts.specialist import PERFORMANCE_SYSTEM_PROMPT
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.router import ModelRouter
from app.application.provisioning.key_resolver import KeyResolver


class PerformanceAnalystNode:
    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()

    async def __call__(self, state: dict) -> dict:
        user_id = state.get("user_id", "")
        route = self.router.get_route("performance_analysis")
        api_key, provider = await self.key_resolver.resolve(user_id, route["model"])
        client = LLMClient(api_key=api_key, provider=provider, model=route["model"])
        findings = {
            "code": state.get("code_findings", []),
            "security": state.get("security_findings", []),
            "architecture": state.get("architecture_findings", []),
        }
        context = state.get("assembled_context", "")

        response = await client.generate([
            {"role": "system", "content": PERFORMANCE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze performance:\n\n{context}\n\nFindings: {findings}"},
        ], max_tokens=route["max_tokens"])

        return {"performance_findings": [response["content"]]}
