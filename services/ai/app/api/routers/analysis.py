from typing import Annotated

import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, field_validator

from app.api.dependencies.auth import JWTPayload, get_current_user
from app.api.dependencies.backpressure import acquire_llm_slot, release_llm_slot
from app.api.dependencies.rate_limiter import check_rate_limit
from app.application.analysis.enrichment import EnrichmentService

# stdlib logging, matching every other module in this service. `services/analysis`
# uses structlog's keyword form; the two services log in different styles and
# matching the local one is what keeps a log line here readable next to the rest
# of this service's output.
logger = logging.getLogger(__name__)

CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]
RateLimit = Annotated[None, Depends(check_rate_limit)]

router = APIRouter(tags=["analysis"])

# Backstop for the whole request, over and above the summary's own deadline.
#
# The summary is bounded inside the service, because a slow summary should cost
# only the summary. This bound is for the other direction: the findings
# enrichment fans out across five categories with `asyncio.gather`, and if the
# provider stalls there is no per-request deadline on it. Without this the
# handler holds a worker, an LLM slot and a rate-limit reservation for as long
# as `LLMClient` is willing to hang, and a caller that gave up at 120s is still
# being charged for the request.
#
# It is a backstop, not the mechanism. It fires when something is genuinely
# stuck; the normal case is that the summary's 75s deadline lands first and
# produces a specific, actionable error instead of a generic 504.
ENRICH_REQUEST_TIMEOUT_SECONDS = 110

_enrichment_service: EnrichmentService | None = None


def _get_enrichment() -> EnrichmentService:
    global _enrichment_service
    if _enrichment_service is None:
        _enrichment_service = EnrichmentService()
    return _enrichment_service


class EnrichFindingItem(BaseModel):
    title: str = ""
    category: str = ""
    severity: str = ""
    description: str = ""
    recommendation: str = ""
    file_path: str = ""
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str = ""
    fix_snippet: str = ""


class EnrichRequest(BaseModel):
    findings: list[EnrichFindingItem]
    overall_score: int | None = None
    tier: str | None = None
    languages: list[str] | None = None
    frameworks: list[str] | None = None


class EnrichedFindingItem(BaseModel):
    title: str = ""
    category: str = ""
    severity: str = ""
    description: str = ""
    recommendation: str = ""
    file_path: str = ""
    line_start: int | None = None
    line_end: int | None = None
    code_snippet: str = ""
    fix_snippet: str = ""
    ai_explanation: str = ""
    ai_recommendation: str = ""
    is_ai_enriched: bool = False


class AiSummaryError(BaseModel):
    """Why the executive summary is missing, in terms a reader can act on.

    Every field here was already computed by `ClassifiedError` and was being
    logged and thrown away. Nothing is added at this layer: the service decides
    what is safe to say, and this schema only refuses to be more permissive than
    that. In particular there is deliberately no `provider`, `model`,
    `technical_message` or raw text field -- adding one would leak the
    provider's verbatim error body, which for an auth failure contains the
    rejected key.
    """

    # `forbid`, not pydantic's default `ignore`. A service that later grows a
    # `provider` field on the envelope would, under `ignore`, be silently
    # forwarded to a browser the moment somebody widened the schema to match --
    # and the widening is exactly the moment nobody is looking at this file. Here
    # it is a construction error instead.
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    suggested_action: str
    # Omitted rather than null when the provider gave no hint, so a client can
    # tell "no hint" from "hint of zero" -- and a zero hint reads as "retry
    # immediately", the opposite of the advice.
    retry_after: float | None = None


class EnrichResponse(BaseModel):
    # Nullable, and typed as such, because "no summary" is now a real state with
    # a reason attached rather than an empty string that could mean anything.
    # `EnrichmentService` already returned `str | None`; this layer was
    # flattening it to `str = ""`, which is where the reason got lost.
    ai_executive_summary: str | None = None
    ai_summary_error: AiSummaryError | None = None
    findings: list[EnrichedFindingItem]

    @field_validator("ai_executive_summary")
    @classmethod
    def _summary_is_absent_or_substantial(cls, value: str | None) -> str | None:
        """Reject a blank summary rather than serialise it.

        `str | None` permits `""`, and that is the specific value this whole
        change is about: it meant both "generation failed" and "no summary was
        requested", so every downstream reader had to guess. The service already
        refuses to produce one -- `_usable_summary` has a length floor -- so this
        does not change any current behaviour. It is here because a *type* is
        advice and a validator is a guarantee, and the guarantee is the part worth
        having: the next person who adds a path that returns `""` gets an error
        rather than a card that silently renders nothing.
        """
        if value is not None and not value.strip():
            raise ValueError(
                "ai_executive_summary must be None or a non-blank string; an empty "
                "string cannot be distinguished from a generation failure"
            )
        return value


@router.post("/v1/analysis/enrich", response_model=EnrichResponse)
async def enrich_analysis(
    request: EnrichRequest,
    http_request: Request,
    _user: CurrentUser,
    _: RateLimit = None,
) -> EnrichResponse:
    # The caller sends `X-Request-ID` and `RequestIDMiddleware` has already put it
    # on `http_request.state`. Logging it here is what makes the header worth
    # sending: without a line carrying it in *this* service's log, a user reporting
    # a missing summary can be traced to the caller-side log entry and nowhere
    # further. Read from state rather than the header so the id logged is the one
    # the middleware actually used, which is also the one echoed on the response.
    #
    # `getattr` with a default because a test that calls the handler directly
    # bypasses the middleware, and a `request.state.request_id` would then be an
    # AttributeError in a function whose job is not to serve the response.
    request_id = getattr(http_request.state, "request_id", None)
    logger.info(
        "ai_enrich_received request_id=%s findings=%d",
        request_id,
        len(request.findings),
    )
    # The route had neither a rate limit nor a backpressure slot, while the
    # sibling `/chat` had both. Enrichment is not a cheap endpoint: it fans out
    # across five finding categories and then runs the summary model loop, all on
    # the shared master key. Unbounded, one user re-running a report could hold
    # every worker in the service.
    await acquire_llm_slot()
    try:
        result = await asyncio.wait_for(
            _get_enrichment().enrich(
                findings=[f.model_dump() for f in request.findings],
                overall_score=request.overall_score,
                tier=request.tier,
                languages=request.languages,
                frameworks=request.frameworks,
            ),
            timeout=ENRICH_REQUEST_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        # A real 504, unlike the summary's timeout. At this point the findings
        # enrichment itself has not returned, so there is nothing to salvage and
        # a degraded 200 would be a lie about work that did not happen.
        raise HTTPException(
            status_code=504,
            detail={
                "error": "enrichment_timeout",
                "message": "AI enrichment took too long. Please try again.",
                "retry_after": 30,
            },
        ) from None
    finally:
        await release_llm_slot()

    # `.get(...)` rather than `result["..."]`: the service is a collaborator
    # across a process boundary, and a missing key should not be a 500 in the
    # middle of a successful enrichment.
    response = EnrichResponse(
        findings=[EnrichedFindingItem(**f) for f in result.get("findings", [])],
        ai_executive_summary=result.get("ai_executive_summary"),
        ai_summary_error=(
            AiSummaryError(**result["ai_summary_error"])
            if result.get("ai_summary_error")
            else None
        ),
    )
    # On the same id, and logged at the same weight whatever the outcome: a
    # caller grepping for a request id needs the one line that tells them whether
    # it produced a summary, and a success-only or failure-only line makes them
    # infer it from the absence of the other.
    logger.info(
        "ai_enrich_completed request_id=%s has_summary=%s error_code=%s",
        request_id,
        response.ai_executive_summary is not None,
        response.ai_summary_error.code if response.ai_summary_error else None,
    )
    return response
