import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AiEnrichmentClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.ai.url.rstrip("/")
        self.endpoint = settings.ai.enrich_endpoint
        self.timeout = settings.ai.timeout
        self.internal_header_name = settings.ai.internal_request_header

    async def enrich_findings(
        self,
        findings: list[dict[str, object]],
        overall_score: int | None = None,
        tier: str | None = None,
        languages: list[str] | None = None,
        frameworks: list[str] | None = None,
    ) -> dict[str, object] | None:
        url = f"{self.base_url}{self.endpoint}"
        logger.info(
            "ai_enrichment_starting",
            url=url,
            findings_count=len(findings),
        )
        payload = {
            "findings": findings,
            "overall_score": overall_score,
            "tier": tier,
            "languages": languages or [],
            "frameworks": frameworks or [],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers={self.internal_header_name: "true"}
                )
                response.raise_for_status()
                data = response.json()
                logger.info("ai_enrichment_success", url=url, status=response.status_code)
                return dict(data)
        except httpx.TimeoutException:
            logger.error(
                "ai_enrichment_timeout",
                url=url,
                timeout=self.timeout,
                exc_info=True,
            )
            return None
        except httpx.HTTPStatusError as e:
            body = (e.response.text[:1000]) if e.response else ""
            logger.error(
                "ai_enrichment_http_error",
                status=e.response.status_code,
                url=url,
                response=body,
            )
            return None
        except Exception as e:
            logger.error(
                "ai_enrichment_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return None
