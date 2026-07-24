import logging
import time

from app.application.agents.prompts.specialist import CODE_ANALYST_SYSTEM_PROMPT
from app.application.provisioning.key_resolver import KeyResolver
from app.infrastructure.llm.client import LLM_SHORT_TIMEOUT
from app.infrastructure.llm.error_classifier import ClassifiedError
from app.infrastructure.llm.failover_engine import FailoverEngine
from app.infrastructure.llm.router import ModelRouter

logger = logging.getLogger(__name__)

SPECIALIST_MAX_TOKENS = 1500


class CodeAnalystNode:
    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()
        self.failover = FailoverEngine(self.key_resolver)

    async def __call__(self, state: dict) -> dict:
        start = time.monotonic()
        user_id = state.get("user_id", "")

        # If a prior node already failed, propagate the error
        if state.get("provider_error"):
            logger.info("node=code_analyst skipped — prior provider_error")
            return {"code_findings": []}

        route = self.router.get_route("code_review")
        context = state.get("assembled_context", "")

        try:
            response = await self.failover.execute(
                [
                    {"role": "system", "content": CODE_ANALYST_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Analyze this code:\n\n{context}\n\nUser message: {state.get('message', '')}",
                    },
                ],
                user_id, route,
                max_tokens=min(route["max_tokens"], SPECIALIST_MAX_TOKENS),
                timeout=LLM_SHORT_TIMEOUT,
            )
        except ClassifiedError as e:
            logger.warning("provider_error node=code_analyst category=%s", e.category.value)
            return {
                "code_findings": [],
                "provider_error": e.user_message,
                "provider_error_category": e.category.value,
                "provider_error_details": {
                    "category": e.category.value,
                    "provider": e.provider,
                    "suggested_action": e.suggested_action.value,
                },
            }

        elapsed = time.monotonic() - start
        tokens_out = response.get("output_tokens", 0)
        logger.info(
            "node=code_analyst elapsed=%.2fs tokens_out=%d model=%s",
            elapsed, tokens_out, route["model"],
        )
        return {"code_findings": [response["content"]]}
