from dataclasses import dataclass
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# The request id, under the name both services agree on. It exists so a user
# reporting "my summary is missing" can be matched to a line in the AI service's
# log without guessing which of several concurrent enrichments they meant.
#
# `app.api.middleware.request_id` declares the same constant, and the AI service has
# its own. This is a deliberate third declaration rather than an import of that
# one: nothing under `app/infrastructure` imports from `app/api` anywhere in this
# service, and an inbound HTTP middleware is not where an outbound client should
# be learning the name of a header. The two constants in this service are the same
# string, and the risk of them drifting is a log line that does not join up rather
# than a security boundary.
REQUEST_ID_HEADER = "X-Request-ID"

# Transport-level failures this client can distinguish, and what to call them.
#
# Every one of these used to `return None`, and the caller could not tell them
# apart: a timeout and a 401 and a connection refusal were one event, logged at
# ERROR with the distinction buried in a message string that no user ever sees.
# They are distinguished now because the reason is the thing that gets stored and
# shown, and "the AI service could not be reached" is not actionable in a way that
# "the request took too long" is not.
_CLIENT_TIMEOUT_CODE = "timeout"
_CLIENT_HTTP_ERROR_CODE = "provider_unavailable"
_CLIENT_TRANSPORT_CODE = "provider_unreachable"


@dataclass(frozen=True)
class EnrichOutcome:
    """What came back, or why nothing did.

    A bare `dict | None` was the wrong shape: `None` cannot say whether the AI
    service was slow, refused the connection, or answered with a 500, and the
    caller could only log a single message covering all three. `error` carries the
    same envelope the AI service produces -- `code`, `message`,
    `suggested_action`, `retry_after` -- so a transport failure and a generation
    failure reach the database in one shape and the UI has one thing to render.
    """

    result: dict[str, object] | None = None
    error: dict[str, object] | None = None

    @property
    def ok(self) -> bool:
        return self.result is not None


def _transport_error(
    code: str, message: str, retry_after: float, retryable: bool = True
) -> dict[str, object]:
    """An envelope in the AI service's shape, for a failure it never got to see.

    Built to the same four-key contract so `_readable_summary_error` narrows it
    without knowing where it came from -- a transport failure that produced a
    different shape would be dropped as unusable, and the reason lost.

    `retryable=False` asks the reader to wait rather than retry. A 401 will not fix
    itself on a timer, so "try again in 30 seconds" is advice that cannot work, and
    following it just produces the same refusal repeatedly.
    """
    return {
        "code": code,
        "message": message,
        "suggested_action": "retry" if retryable else "wait",
        "retry_after": retry_after,
    }


class AiEnrichmentClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.ai.url.rstrip("/")
        self.endpoint = settings.ai.enrich_endpoint
        self.timeout = settings.ai.timeout
        self.internal_header_name = settings.ai.internal_request_header
        self.internal_secret = settings.jwt.internal_request_secret

    async def enrich_findings(
        self,
        findings: list[dict[str, object]],
        overall_score: int | None = None,
        tier: str | None = None,
        languages: list[str] | None = None,
        frameworks: list[str] | None = None,
    ) -> EnrichOutcome:
        url = f"{self.base_url}{self.endpoint}"
        request_id = uuid4().hex
        logger.info(
            "ai_enrichment_starting",
            url=url,
            findings_count=len(findings),
            request_id=request_id,
        )
        payload = {
            "findings": findings,
            "overall_score": overall_score,
            "tier": tier,
            "languages": languages or [],
            "frameworks": frameworks or [],
        }
        headers = {
            self.internal_header_name: self.internal_secret,
            REQUEST_ID_HEADER: request_id,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "ai_enrichment_success",
                    url=url,
                    status=response.status_code,
                    request_id=request_id,
                )
                return EnrichOutcome(result=dict(data))
        except httpx.TimeoutException:
            logger.error(
                "ai_enrichment_timeout",
                url=url,
                timeout=self.timeout,
                request_id=request_id,
                exc_info=True,
            )
            return EnrichOutcome(
                error=_transport_error(
                    _CLIENT_TIMEOUT_CODE,
                    "The AI service took too long to respond. Your findings are "
                    "unaffected -- try again for the AI summary.",
                    30,
                )
            )
        except httpx.HTTPStatusError as e:
            # The body is logged, not forwarded. It is the AI service's own error
            # page or proxy output, which can contain internal detail; it belongs
            # in the logs, and the envelope carries the reason instead.
            body = (e.response.text[:1000]) if e.response else ""
            status = e.response.status_code if e.response else 0
            logger.error(
                "ai_enrichment_http_error",
                status=status,
                url=url,
                response=body,
                request_id=request_id,
            )
            # 5xx is the AI service failing; 4xx is this request being refused, and
            # a 401 will not fix itself by retrying while a 503 usually will. The
            # message says which, because "try again" is the wrong advice for the
            # first.
            retryable = status >= 500 or status in (408, 429)
            return EnrichOutcome(
                error=_transport_error(
                    _CLIENT_HTTP_ERROR_CODE,
                    (
                        f"The AI service returned an error ({status}). Your "
                        "findings are unaffected."
                        if retryable
                        else f"The AI service rejected this request ({status}). "
                        "Your findings are unaffected."
                    ),
                    30 if retryable else 0,
                    retryable=retryable,
                )
            )
        except Exception as e:
            # Deliberately the last arm, and deliberately does not re-raise. The
            # findings enrichment failing must not fail the job -- but it now says
            # which of several causes it was, instead of one message for all of
            # them.
            logger.error(
                "ai_enrichment_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
                request_id=request_id,
                exc_info=True,
            )
            return EnrichOutcome(
                error=_transport_error(
                    _CLIENT_TRANSPORT_CODE,
                    "The AI service could not be reached. Your findings are "
                    "unaffected -- try again for the AI summary.",
                    30,
                )
            )
