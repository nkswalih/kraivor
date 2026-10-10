"""ExplainerNode — synthesizes multi-agent results into a grounded, intent-aware response."""

import logging
import re
from datetime import datetime, UTC

from app.application.agents.prompts.specialist import (
    EXPLAINER_SYSTEM_PROMPT,
    EXPLAINER_EVIDENCE_PROMPT,
    EXPLAINER_CASUAL_PROMPT,
    EXPLAINER_CODE_AUDIT_PROMPT,
    EXPLAINER_GENERAL_QA_PROMPT,
)
from app.application.provisioning.key_resolver import KeyResolver
from app.infrastructure.llm.error_classifier import ClassifiedError, ErrorCategory
from app.infrastructure.llm.failover_engine import FailoverEngine
from app.infrastructure.llm.router import ModelRouter

logger = logging.getLogger(__name__)


def _format_prompt(
    template: str, user_name: str | None, user_context: str | None
) -> str:
    name = user_name or "the user"
    ctx = f"Known context about the user:\n{user_context}" if user_context else ""
    return template.format(user_name=name, user_context=ctx)


_AUDIT_INTENTS = {"repository_analysis", "security_analysis", "architecture_review", "performance_analysis"}
_CASUAL_INTENTS = {"greeting", "conversation"}


def _inject_date(prompt: str) -> str:
    """Prepend current date to any system prompt so the LLM knows today's date."""
    now = datetime.now(UTC)
    date_line = (
        f"CURRENT DATE & TIME: {now.strftime('%A, %B %d, %Y — %H:%M UTC')}. "
        "Use this as your time reference. "
        "NEVER state a different date or year unless explicitly told otherwise.\n\n"
    )
    return date_line + prompt


def _select_prompt(intent: str | None, has_findings: bool, has_evidence: bool, has_user_context: bool) -> str:
    """Select the appropriate explainer prompt based on intent and available data."""
    if intent in _CASUAL_INTENTS:
        return EXPLAINER_CASUAL_PROMPT
    if intent in _AUDIT_INTENTS and has_findings:
        return EXPLAINER_CODE_AUDIT_PROMPT
    if has_evidence:
        return EXPLAINER_EVIDENCE_PROMPT
    if has_user_context:
        return EXPLAINER_GENERAL_QA_PROMPT
    return EXPLAINER_SYSTEM_PROMPT


def _validate_sources(response: str, sources: list[dict]) -> str:
    """Anti-hallucination gate: strip fabricated file paths and flag unsupported claims."""
    file_patterns = re.findall(r'(?:^|\s)(?:/[\w.-]+){2,}[\w.-]*', response)
    file_patterns += re.findall(r'(?:^|\s)(?:[\w-]+/){2,}[\w.-]+', response)
    code_block_files = re.findall(r'###\s+([\w/._-]+\.\w+)', response)

    if file_patterns or code_block_files:
        has_code_sources = any(
            s.get("provider") in ("github", "documentation")
            for s in sources
        )
        if not has_code_sources and sources:
            disclaimer = (
                "\n\n> **Note:** The file paths shown above are illustrative examples "
                "based on common project structures. For exact paths in your codebase, "
                "please run a code search or specify the repository."
            )
            if "illustrative examples" not in response:
                response += disclaimer

    return response


def _build_fallback_response(state: dict, error: ClassifiedError) -> str:
    """When LLM is unavailable, return raw findings from analysts."""
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

    evidence = state.get("evidence")
    tool_results = state.get("tool_results")

    parts = [f"**AI Service Error:** {error.user_message}\n"]

    if findings:
        parts.append("**Raw Analysis:**\n" + "\n\n".join(findings))
    if evidence:
        parts.append(f"**Research Sources:**\n{evidence}")
    if tool_results:
        parts.append(f"**Workspace Data:**\n{tool_results}")

    if len(parts) == 1:
        parts.append(
            "Please try again or switch to a different model in Settings."
        )

    return "\n\n".join(parts)


class ExplainerNode:
    def __init__(self):
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()
        self.failover = FailoverEngine(self.key_resolver)

    async def __call__(self, state: dict) -> dict:
        user_id = state.get("user_id", "")
        user_name = state.get("user_name")
        user_context = state.get("user_context")
        intent = state.get("intent")
        user_model = state.get("model")
        low_confidence = state.get("low_confidence", False)

        # If a prior node already set a provider error, degrade gracefully
        # by returning raw findings without calling the LLM.
        prior_error = state.get("provider_error")
        if prior_error:
            error_category = state.get("provider_error_category", "unknown")
            error_details = state.get("provider_error_details") or {}
            fake_error = ClassifiedError(
                category=ErrorCategory(error_category) if error_category in ErrorCategory.__members__.values() else ErrorCategory.UNKNOWN,
                provider=error_details.get("provider", "unknown"),
                model=state.get("model") or "unknown",
                user_message=prior_error,
                technical_message=prior_error,
                suggested_action=error_details.get("suggested_action", "retry"),
            )
            return {
                "response": _build_fallback_response(state, fake_error),
                "provider_error": prior_error,
            }

        route = self.router.get_route_for_user("code_review", user_model)

        # Collect specialist findings
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
        evidence = state.get("evidence")
        evidence_sources = state.get("evidence_sources") or []

        has_findings = bool(findings)
        has_evidence = bool(evidence)
        has_user_context = bool(user_context)

        prompt_template = _select_prompt(intent, has_findings, has_evidence, has_user_context)

        # Build user message — user context FIRST as primary knowledge source
        parts = []

        if user_context:
            parts.append(f"## What you know about this user and their projects\n{user_context}")

        parts.append(f"## User's question\n{user_msg}")

        if evidence:
            parts.append(f"## Verified research sources\n{evidence}")

        if tool_results:
            parts.append(f"## Workspace data\n{tool_results}")

        if context:
            parts.append(f"## Repository context\n{context}")

        if findings:
            parts.append("## Analysis findings\n" + "\n\n".join(findings))

        if history:
            brief = "\n".join(
                f"{'User' if h.get('role') == 'user' else 'Assistant'}: {h.get('content', '')[:500]}"
                for h in history[-15:]
            )
            parts.append(f"## Recent conversation\n{brief}")

        messages = [
            {
                "role": "system",
                "content": _inject_date(_format_prompt(prompt_template, user_name, user_context)),
            },
            {"role": "user", "content": "\n\n".join(parts)},
        ]

        try:
            response = await self.failover.execute(
                messages, user_id, route, max_tokens=route["max_tokens"],
            )
        except ClassifiedError as e:
            logger.warning("provider_error node=explainer category=%s", e.category.value)
            return {
                "response": _build_fallback_response(state, e),
                "provider_error": e.user_message,
                "provider_error_category": e.category.value,
                "provider_error_details": {
                    "category": e.category.value,
                    "provider": e.provider,
                    "suggested_action": e.suggested_action.value,
                },
            }

        response_text = response["content"]

        if evidence_sources:
            response_text = _validate_sources(response_text, evidence_sources)

        # Fix 14: Surface grounding confidence — append caveat if evidence was low-quality
        if low_confidence and "Low-confidence" not in (evidence or ""):
            response_text += (
                "\n\n> **Note:** This response is based on limited sources and may not "
                "be fully verified. Please cross-check critical information."
            )

        return {"response": response_text, "usage": response}
