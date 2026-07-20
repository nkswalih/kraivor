import logging
import time

from app.application.agents.prompts.specialist import SECURITY_SYSTEM_PROMPT
from app.application.provisioning.key_resolver import KeyResolver
from app.infrastructure.llm.client import LLMClient, LLM_SHORT_TIMEOUT
from app.infrastructure.llm.router import ModelRouter

logger = logging.getLogger(__name__)

SPECIALIST_MAX_TOKENS = 1200


class SecurityAnalystNode:
    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()

    async def __call__(self, state: dict) -> dict:
        start = time.monotonic()
        user_id = state.get("user_id", "")
        route = self.router.get_route("security_analysis")
        api_key, provider = await self.key_resolver.resolve(user_id, route["model"])
        client = LLMClient(api_key=api_key, provider=provider, model=route["model"])
        code = state.get("code_findings", [])
        context = state.get("assembled_context", "")

        response = await client.generate(
            [
                {"role": "system", "content": SECURITY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Analyze for vulnerabilities:\n\n{context}\n\nCode findings: {code}",
                },
            ],
            max_tokens=min(route["max_tokens"], SPECIALIST_MAX_TOKENS),
            timeout=LLM_SHORT_TIMEOUT,
        )

        elapsed = time.monotonic() - start
        tokens_out = response.get("output_tokens", 0)
        logger.info(
            "node=security_analyst elapsed=%.2fs tokens_out=%d provider=%s model=%s",
            elapsed, tokens_out, provider, route["model"],
        )
        return {"security_findings": [response["content"]]}
