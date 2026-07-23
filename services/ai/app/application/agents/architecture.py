import logging
import time

from app.application.agents.prompts.specialist import ARCHITECTURE_SYSTEM_PROMPT
from app.application.provisioning.key_resolver import KeyResolver
from app.infrastructure.llm.error_classifier import ClassifiedError
from app.infrastructure.llm.failover_engine import FailoverEngine
from app.infrastructure.llm.router import ModelRouter

logger = logging.getLogger(__name__)

SPECIALIST_MAX_TOKENS = 1200


class ArchitectureAnalystNode:
    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()
        self.failover = FailoverEngine(self.key_resolver)

    async def __call__(self, state: dict) -> dict:
        start = time.monotonic()
        user_id = state.get("user_id", "")

        if state.get("provider_error"):
            logger.info("node=architecture_analyst skipped — prior provider_error")
            return {"architecture_findings": []}

        route = self.router.get_route("architecture_review")
        findings = {
            "code": state.get("code_findings", []),
            "security": state.get("security_findings", []),
        }
        context = state.get("assembled_context", "")

        try:
            response = await self.failover.execute(
                [
                    {"role": "system", "content": ARCHITECTURE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Review architecture:\n\n{context}\n\nFindings: {findings}",
                    },
                ],
                user_id, route,
                max_tokens=min(route["max_tokens"], SPECIALIST_MAX_TOKENS),
                timeout=25,
            )
        except ClassifiedError as e:
            logger.warning("provider_error node=architecture_analyst category=%s", e.category.value)
            return {
                "architecture_findings": [],
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
            "node=architecture_analyst elapsed=%.2fs tokens_out=%d model=%s",
            elapsed, tokens_out, route["model"],
        )
        return {"architecture_findings": [response["content"]]}
