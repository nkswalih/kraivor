from app.application.agents.prompts.specialist import CODE_ANALYST_SYSTEM_PROMPT
from app.application.provisioning.key_resolver import KeyResolver
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.router import ModelRouter


class CodeAnalystNode:
    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()

    async def __call__(self, state: dict) -> dict:
        user_id = state.get("user_id", "")
        route = self.router.get_route("code_review")
        api_key, provider = await self.key_resolver.resolve(user_id, route["model"])
        client = LLMClient(api_key=api_key, provider=provider, model=route["model"])
        context = state.get("assembled_context", "")

        response = await client.generate(
            [
                {"role": "system", "content": CODE_ANALYST_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Analyze this code:\n\n{context}\n\nUser message: {state.get('message', '')}",
                },
            ],
            max_tokens=route["max_tokens"],
        )

        return {"code_findings": [response["content"]]}
