import asyncio
import logging

from app.core.config import settings
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.error_classifier import (
    ClassifiedError,
    ErrorCategory,
    SuggestedAction,
    classify_error,
)
from app.infrastructure.llm.router import FREE_MODELS, ModelRouter

logger = logging.getLogger(__name__)

# How many of `FREE_MODELS` to try before giving up on the summary.
#
# The loop used to walk all nine, and each attempt was three retries at a 45s
# timeout -- roughly 1250s in the worst case, against a client (`services/analysis`
# config) that gives up at 120s and writes "AI enrichment skipped" into a progress
# message no screen renders. So the worst case was not slow, it was invisible: the
# worker was pinned and the user saw nothing at all.
#
# Four is enough to clear a single-model outage or a model that has quietly been
# retired from the free tier, which is the failure this loop exists for, and it
# cuts the worst case by more than half. The findings are enriched by a separate
# per-category path, so a summary that gives up costs one paragraph, not the report.
MAX_SUMMARY_MODEL_ATTEMPTS = 4

# Wall-clock budget for the whole summary attempt, across all models.
#
# Set below the 120s the analysis service allows for the entire enrich call, and
# below the 90s the AI service uses as its own LLM chain budget, for the reason
# given at the call site: a deadline that races the caller's own timeout is not a
# deadline. 75s leaves room for the findings enrichment that has already run and
# for the response to be serialised before the caller's clock expires.
#
# 75s is also comfortably more than the cap needs: four models at a 45s client
# timeout is 180s, so in the worst case this is what stops the loop rather than
# the loop stopping itself -- which is the point of having it, since a client
# timeout is not a decision this code gets to make.
SUMMARY_TIMEOUT_SECONDS = 75

# A summary shorter than this is not a summary.
#
# `LLMClient.generate` already strips `<think>` blocks, so a reasoning model that
# spent its whole budget thinking returns `""`. Returning that as a successful
# summary is what made this failure invisible in the first place: the analysis
# service logged "AI service returned empty ai_executive_summary -- LLM generation
# may have failed" at WARNING, and the user was shown an empty card. Two sentences
# is the floor the prompt itself asks for ("Overall assessment (1-2 sentences)").
MIN_SUMMARY_CHARS = 80

# Responses that are a refusal or a meta-comment rather than a summary. Matched on
# the opening because a model asked for Markdown sometimes prefixes a note, and
# only the first line distinguishes that from a real summary that happens to
# contain the words later on.
_REFUSAL_PREFIXES = (
    "i'm sorry",
    "i am sorry",
    "i cannot",
    "i can't",
    "i'm unable",
    "i am unable",
    "as an ai",
    "i'm not able",
    "i am not able",
    "sorry, ",
    "no summary",
)


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


def describe_summary_failure(error: ClassifiedError) -> dict[str, object]:
    """Reduce a `ClassifiedError` to the four fields a client may see.

    This function is the boundary. `ClassifiedError` carries `technical_message`,
    `provider` and `model` alongside the user-facing metadata, and those three are
    the ones that must never reach a browser: `technical_message` is the provider's
    verbatim response, which for an auth failure routinely contains the rejected
    key, and the model name is an internal routing decision a user cannot act on.

    So the envelope is built from named fields rather than by copying and deleting,
    because a copy-then-delete approach fails the first time someone adds a field to
    `ClassifiedError` -- the new field is copied and the delete list is not updated.

    `code` is the enum's string value rather than its name, and is the one value the
    frontend switches on. `retry_after` is omitted rather than sent as null when
    there is no hint, so the client can distinguish "no hint" from "hint of zero".
    """
    envelope: dict[str, object] = {
        "code": error.category.value,
        "message": error.user_message,
        "suggested_action": error.suggested_action.value,
    }
    if error.retry_after is not None:
        envelope["retry_after"] = error.retry_after
    return envelope


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

        # Parallelize category enrichment with concurrency limit
        semaphore = asyncio.Semaphore(4)

        async def _enrich_with_semaphore(category, cat_findings):
            async with semaphore:
                return category, await self._enrich_category(category, cat_findings)

        tasks = [
            _enrich_with_semaphore(cat, cat_findings)
            for cat, cat_findings in grouped.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        enriched_map: dict[str, list[dict]] = {}
        for result in results:
            if isinstance(result, Exception):
                logger.warning("category_enrichment_gather_failed error=%s", str(result))
                continue
            category, cat_results = result
            enriched_map[category] = cat_results

        # Fallback for categories that failed
        for cat, cat_findings in grouped.items():
            if cat not in enriched_map:
                enriched_map[cat] = [
                    {**f, "ai_explanation": ""} for f in cat_findings
                ]

        enriched_findings: list[dict] = []
        for _category, cat_results in enriched_map.items():
            for item in cat_results:
                enriched_findings.append(item)

        # The summary is one field of a large response. Losing it must not lose
        # the findings it was summarising, so this is a degraded result rather
        # than a raised error -- but it is no longer a *silent* one.
        #
        # It used to be `ai_executive_summary = ""` with a WARNING log, which
        # made four different situations indistinguishable to everyone downstream:
        # the provider failed, no key is configured, generation is still running,
        # and the model genuinely had nothing to say. This service already knows
        # which one it is -- `ClassifiedError` carries a category, a user-facing
        # message, a suggested action and a retry hint -- and threw all of it
        # away at the catch below. The envelope now forwards only that computed
        # metadata. `technical_message`, the provider name, the model and the key
        # never leave this process.
        ai_executive_summary: str | None = None
        ai_summary_error: dict[str, object] | None = None
        try:
            # A deadline on the summary, and specifically not on the response.
            #
            # `services/analysis` configures a 120s timeout on this call and
            # treats a timeout as the whole enrichment having failed. Putting a
            # deadline here rather than at the route means a slow *summary* costs
            # the summary and nothing else, instead of costing the findings that
            # were already computed and are sitting in memory a line below.
            #
            # The budget is deliberately below the client's, not equal to it. A
            # deadline that fires at the same moment the client gives up is not a
            # deadline; it is a coin toss decided by scheduling, and the losing
            # side reports a transport error for something that was only ever
            # slow. `MAX_SUMMARY_MODEL_ATTEMPTS` bounds the worst case at roughly
            # 540s, so without this the client almost always times out first.
            ai_executive_summary = await asyncio.wait_for(
                self._generate_executive_summary(
                    enriched_findings, overall_score, tier, languages, frameworks
                ),
                timeout=SUMMARY_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            # A distinct arm, not the generic `Exception` one below. The generic
            # arm would classify this via `classify_error`, which reads
            # `str(exc)`, and a bare `TimeoutError` stringifies to nothing useful
            # -- so it would arrive as `unknown` with "Something went wrong".
            # The truth is more specific and more actionable than that: the model
            # was reachable and simply too slow, which is worth retrying and is
            # not the same as a provider that is down.
            ai_summary_error = describe_summary_failure(
                ClassifiedError(
                    category=ErrorCategory.TIMEOUT,
                    provider="openrouter",
                    model="unknown",
                    user_message=(
                        "The AI model took too long to write a summary. Your "
                        "findings are unaffected -- try again for the summary."
                    ),
                    technical_message=f"summary exceeded {SUMMARY_TIMEOUT_SECONDS}s",
                    suggested_action=SuggestedAction.RETRY,
                    retry_after=30,
                )
            )
            logger.warning(
                "executive_summary_generation_timed_out",
                extra={"timeout_seconds": SUMMARY_TIMEOUT_SECONDS},
            )
        except ClassifiedError as e:
            ai_summary_error = describe_summary_failure(e)
            logger.warning(
                "executive_summary_generation_failed",
                extra={
                    "category": e.category.value,
                    "provider": e.provider,
                    "model": e.model,
                    "retry_after": e.retry_after,
                },
            )
        except Exception as e:  # noqa: BLE001
            # Anything unclassified still has to reach the user as *something*.
            # Losing the summary without saying so is the defect being fixed, so
            # the catch cannot simply re-raise: an unexpected error type would
            # take the findings down with it, which is worse than an unclassified
            # message. Classifying it keeps this a degraded 200 carrying an honest
            # code, instead of a 500 that discards the whole report.
            ai_summary_error = describe_summary_failure(
                classify_error(e, provider="openrouter", model="unknown")
            )
            logger.warning(
                "executive_summary_generation_failed_unclassified", exc_info=True
            )

        return {
            "findings": enriched_findings,
            "ai_executive_summary": ai_executive_summary,
            "ai_summary_error": ai_summary_error,
        }

    async def _enrich_category(self, category: str, findings: list[dict]) -> list[dict]:
        route_key = CATEGORY_ROUTES.get(category, "code_review")
        route = self.router.get_route(route_key)

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

        last_error: Exception | None = None
        for model in FREE_MODELS:
            try:
                client = LLMClient(
                    api_key=settings.openrouter__master__key,
                    provider="openrouter",
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
                    items = (
                        parsed
                        if isinstance(parsed, list)
                        else parsed.get("findings", parsed.get("items", []))
                    )
                    for item in items:
                        idx = item.get("index", 0)
                        if 1 <= idx <= len(findings):
                            enriched_finding = dict(findings[idx - 1])
                            enriched_finding["ai_explanation"] = item.get(
                                "ai_explanation", ""
                            )
                            enriched_finding["ai_recommendation"] = item.get(
                                "ai_recommendation", ""
                            )
                            enriched_finding["is_ai_enriched"] = True
                            enriched_items.append(enriched_finding)
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
                    logger.warning(
                        "failed_to_parse_enrichment_response category=%s model=%s error=%s",
                        category,
                        model,
                        str(e),
                    )
                    raise

                remaining = len(findings) - len(enriched_items)
                if remaining > 0:
                    for f in findings[len(enriched_items) :]:
                        enriched_finding = dict(f)
                        enriched_finding["ai_explanation"] = ""
                        enriched_finding["is_ai_enriched"] = False
                        enriched_items.append(enriched_finding)

                return enriched_items
            except Exception as e:
                last_error = e
                logger.warning(
                    "enrichment_model_failed model=%s category=%s error=%s",
                    model,
                    category,
                    str(e),
                )
                continue

        # FREE_MODELS is a module-level list and could be empty, in which
        # case last_error is still None and `raise last_error` would itself
        # raise TypeError. Raise a real exception instead.
        if last_error is not None:
            raise last_error
        raise RuntimeError(
            f"No free enrichment models configured for category {category!r}"
        )

    async def _generate_executive_summary(
        self,
        findings: list[dict],
        overall_score: int | None,
        tier: str | None,
        languages: list[str] | None,
        frameworks: list[str] | None,
    ) -> str:
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

        critical = [
            f for f in findings if str(f.get("severity", "")).upper() == "CRITICAL"
        ]
        high = [f for f in findings if str(f.get("severity", "")).upper() == "HIGH"]
        categories = {f.get("category", "") for f in findings}

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

        # Short-circuit before the loop.
        #
        # With no master key this used to walk every model, and every model failed
        # identically at the client with an empty key -- three retries and a 45s
        # timeout apiece, all of it certain. That is the single most common real
        # failure on this path (a deployment without an AI key configured) and it
        # was also the slowest, because it was treated as a transient failure
        # rather than as the missing configuration it is.
        api_key = settings.openrouter__master__key
        if not api_key:
            raise ClassifiedError(
                category=ErrorCategory.PROVIDER_NOT_CONFIGURED,
                provider="openrouter",
                model="none",
                user_message=(
                    "The AI service is not configured on this server, so no "
                    "executive summary could be generated. Your findings are "
                    "unaffected."
                ),
                technical_message="openrouter master key is not set",
                suggested_action=SuggestedAction.ADD_KEY,
            )

        candidates = FREE_MODELS[:MAX_SUMMARY_MODEL_ATTEMPTS]
        last_error: ClassifiedError | None = None

        for model in candidates:
            try:
                client = LLMClient(api_key=api_key, provider="openrouter", model=model)
                result = await client.generate(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.4,
                    max_tokens=1024,
                )

                content = _usable_summary(result.get("content"))
                if content is not None:
                    return content

                # A response arrived and it was not usable. This is a different
                # failure from a provider error and must not be counted as
                # "try the next model" without a reason -- an empty string and a
                # refusal both usually mean the same thing upstream (the model
                # spent its budget on `<think>` blocks, or declined), so trying
                # four models is unlikely to help where one did not. It is
                # recorded and the loop continues, but the final report names this
                # rather than blaming the last model's transport.
                logger.warning(
                    "summary_model_returned_unusable_content", extra={"model": model}
                )
                last_error = ClassifiedError(
                    category=ErrorCategory.UNKNOWN,
                    provider="openrouter",
                    model=model,
                    user_message=(
                        "The AI model returned an empty response instead of a "
                        "summary. Please try again."
                    ),
                    technical_message="empty or refusal-shaped summary content",
                    suggested_action=SuggestedAction.RETRY,
                )
                continue
            except ClassifiedError:
                raise
            except Exception as e:
                # Classified per attempt rather than once at the end, because the
                # categories differ per model: one model can be retired from the
                # free tier (switch) while the account itself is rate limited
                # (wait), and the report should name whichever is the real reason
                # the first one -- not whatever the last model happened to say.
                last_error = classify_error(e, provider="openrouter", model=model)
                logger.warning(
                    "summary_model_failed",
                    extra={
                        "model": model,
                        "category": last_error.category.value,
                        "status_code": last_error.metadata.get("status_code"),
                    },
                )
                continue

        if last_error is not None:
            raise last_error
        # Only reachable if `FREE_MODELS` is empty or every entry was filtered out
        # -- which is a configuration fault here rather than anything a retry fixes.
        raise ClassifiedError(
            category=ErrorCategory.ALL_MODELS_FAILED,
            provider="openrouter",
            model="none",
            user_message=(
                "No AI models are available to generate a summary. Please try "
                "again later."
            ),
            technical_message="FREE_MODELS is empty",
            suggested_action=SuggestedAction.RETRY,
        )


def _usable_summary(content: object) -> str | None:
    """The generated text, or None if it is not something to call a summary.

    `client.generate` already returns a string with `<think>` blocks stripped, so
    the three shapes rejected here are the ones that survive that:

      * `""` -- a reasoning model that spent its entire budget thinking. This is
        the common one, and it used to be persisted verbatim as a successful
        summary.
      * whitespace only -- same outcome, less obviously so.
      * a refusal -- the model declined, and the reason it declined is very likely
        to contain instructions or excerpts rather than an assessment, so passing
        it through would put model-authored text in front of a reader as if a
        person had written it.

    Returns None rather than raising, so the caller can decide whether to try the
    next model; the reason it rejected is not worth a second error type, because
    all three look the same to whoever reads the report.
    """
    if not isinstance(content, str):
        return None

    text = content.strip()
    if len(text) < MIN_SUMMARY_CHARS:
        return None

    # Only the first line decides: a real summary may well contain "I cannot
    # recommend shipping this" further down, and that is the model doing its job.
    first_line = text.splitlines()[0].strip().lower() if text.splitlines() else ""
    if any(first_line.startswith(prefix) for prefix in _REFUSAL_PREFIXES):
        return None

    return text
