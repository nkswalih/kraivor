import logging
from collections.abc import Sequence

from app.core.config import settings
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.router import ModelRouter

logger = logging.getLogger(__name__)


CATEGORY_PROMPTS: dict[str, str] = {
    "security": (
        "You are a security expert. For each finding below, provide a detailed "
        "explanation of the vulnerability, why it matters, and an actionable fix. "
        "Rate severity: CRITICAL, HIGH, MEDIUM, LOW.\n\n"
    ),
    "code_quality": (
        "You are a senior code reviewer. For each finding below, explain the code quality "
        "issue, the anti-pattern or bug involved, and how to fix it properly.\n\n"
    ),
    "performance": (
        "You are a performance engineer. For each finding below, explain the performance "
        "bottleneck, its expected impact (include Big-O if relevant), and how to resolve it.\n\n"
    ),
    "architecture": (
        "You are a solutions architect. For each finding below, explain the architectural "
        "concern, why it affects maintainability or scalability, and specific recommendations "
        "for improvement.\n\n"
    ),
    "devops": (
        "You are a DevOps engineer. For each finding below, explain the infrastructure or "
        "deployment issue, its production impact, and the recommended fix.\n\n"
    ),
    "reliability": (
        "You are a reliability engineer. For each finding below, explain the reliability "
        "concern, how it could cause production incidents, and the best remediation.\n\n"
    ),
    "dead_code": (
        "You are a code quality specialist. For each dead code finding below, explain why "
        "it's problematic for maintainability and how to safely remove it.\n\n"
    ),
    "error_detection": (
        "You are a software reliability expert. For each error-handling finding below, explain "
        "the risk of the current pattern and recommend a robust alternative.\n\n"
    ),
}


CATEGORY_ROUTES: dict[str, str] = {
    "security": "security_analysis",
    "code_quality": "code_review",
    "performance": "performance_analysis",
    "architecture": "architecture_review",
    "devops": "code_review",
    "reliability": "code_review",
    "dead_code": "code_review",
    "error_detection": "code_review",
}


class EnrichmentService:
    def __init__(self) -> None:
        self.router = ModelRouter()

    async def enrich(
        self,
        findings: list[dict],
        overall_score: int | None = None,
        tier: str | None = None,
        languages: list[str] | None = None,
        frameworks: list[str] | None = None,
    ) -> dict:
        grouped: dict[str, list[dict]] = {}
        for f in findings:
            cat = f.get("category", "unknown")
            grouped.setdefault(cat, []).append(f)

        enriched_map: dict[str, list[dict]] = {}
        for category, cat_findings in grouped.items():
            try:
                result = await self._enrich_category(category, cat_findings)
                enriched_map[category] = result
            except Exception as e:
                logger.warning("category_enrichment_failed", category=category, error=str(e))
                enriched_map[category] = [
                    {**f, "ai_explanation": ""} for f in cat_findings
                ]

        enriched_findings: list[dict] = []
        for category, cat_results in enriched_map.items():
            for item in cat_results:
                enriched_findings.append(item)

        ai_executive_summary = ""
        try:
            ai_executive_summary = await self._generate_executive_summary(
                enriched_findings, overall_score, tier, languages, frameworks,
            )
        except Exception as e:
            logger.warning("executive_summary_generation_failed", error=str(e))

        return {
            "findings": enriched_findings,
            "ai_executive_summary": ai_executive_summary,
        }

    async def _enrich_category(
        self, category: str, findings: list[dict],
    ) -> list[dict]:
        route_key = CATEGORY_ROUTES.get(category, "code_review")
        route = self.router.get_route(route_key)
        model = route["model"]

        system_prompt = CATEGORY_PROMPTS.get(
            category,
            "You are a code analyst. For each finding below, explain the issue "
            "and recommend a fix.\n\n",
        )

        findings_text = ""
        for i, f in enumerate(findings, 1):
            findings_text += (
                f"--- Finding {i} ---\n"
                f"Title: {f.get('title', '')}\n"
                f"Severity: {f.get('severity', '')}\n"
                f"File: {f.get('file_path', '')}:{f.get('line_start', '') or ''}\n"
                f"Description: {f.get('description', '')[:500]}\n"
                f"Code:\n```\n{f.get('code_snippet', '')[:1000]}\n```\n\n"
            )

        user_prompt = (
            f"Analyze these {category} findings and for EACH one provide:\n"
            f"1. A detailed explanation of why this is an issue\n"
            f"2. An actionable fix recommendation\n\n"
            f"Respond with a JSON array of objects, each with fields:\n"
            f'  - "index": the finding number\n'
            f'  - "ai_explanation": your detailed explanation\n'
            f'  - "ai_recommendation": actionable fix steps\n\n'
            f"Findings:\n{findings_text}"
        )

        client = LLMClient(
            api_key=settings.openrouter__master__key,
            provider=model.split("/")[0],
            model=model,
        )
        result = await client.generate(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=route.get("max_tokens", 4096),
            response_format={"type": "json_object"},
        )

        enriched_items: list[dict] = []
        try:
            import json
            parsed = json.loads(result["content"])
            items = parsed if isinstance(parsed, list) else parsed.get("findings", parsed.get("items", []))
            for item in items:
                idx = item.get("index", 0)
                if 1 <= idx <= len(findings):
                    enriched_finding = dict(findings[idx - 1])
                    enriched_finding["ai_explanation"] = item.get("ai_explanation", "")
                    enriched_finding["ai_recommendation"] = item.get("ai_recommendation", "")
                    enriched_finding["is_ai_enriched"] = True
                    enriched_items.append(enriched_finding)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("failed_to_parse_enrichment_response", category=category, error=str(e))
            for f in findings:
                enriched_finding = dict(f)
                enriched_finding["ai_explanation"] = ""
                enriched_finding["is_ai_enriched"] = False
                enriched_items.append(enriched_finding)

        remaining = len(findings) - len(enriched_items)
        if remaining > 0:
            for f in findings[len(enriched_items):]:
                enriched_finding = dict(f)
                enriched_finding["ai_explanation"] = ""
                enriched_finding["is_ai_enriched"] = False
                enriched_items.append(enriched_finding)

        return enriched_items

    async def _generate_executive_summary(
        self,
        findings: list[dict],
        overall_score: int | None,
        tier: str | None,
        languages: list[str] | None,
        frameworks: list[str] | None,
    ) -> str:
        route = self.router.get_route("architecture_review")
        model = route["model"]

        system_prompt = (
            "You are a technical lead writing an executive summary of a production readiness "
            "analysis. Synthesize the findings below into a clear, actionable narrative.\n\n"
            "Structure:\n"
            "1. Overall assessment (1-2 sentences)\n"
            "2. Key strengths (if any)\n"
            "3. Critical issues to address (by priority)\n"
            "4. Recommended next steps\n\n"
            "Be concise and business-focused. Use Markdown."
        )

        critical = [f for f in findings if str(f.get("severity", "")).upper() == "CRITICAL"]
        high = [f for f in findings if str(f.get("severity", "")).upper() == "HIGH"]
        categories = set(f.get("category", "") for f in findings)

        user_prompt = (
            f"Overall Score: {overall_score or 'N/A'}/100\n"
            f"Tier: {tier or 'N/A'}\n"
            f"Languages: {', '.join(languages) if languages else 'N/A'}\n"
            f"Frameworks: {', '.join(frameworks) if frameworks else 'N/A'}\n"
            f"Total Findings: {len(findings)}\n"
            f"Critical: {len(critical)}\n"
            f"High: {len(high)}\n"
            f"Categories: {', '.join(sorted(categories))}\n\n"
        )

        if critical:
            user_prompt += "Critical Issues:\n"
            for f in critical:
                user_prompt += f"- {f.get('title', '')} ({f.get('file_path', '')})\n"
            user_prompt += "\n"

        if high:
            user_prompt += "High Severity Issues:\n"
            for f in high[:10]:
                user_prompt += f"- {f.get('title', '')} ({f.get('file_path', '')})\n"

        client = LLMClient(
            api_key=settings.openrouter__master__key,
            provider=model.split("/")[0],
            model=model,
        )
        result = await client.generate(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=1024,
        )

        return result["content"]
