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

    async def enrich_findings(
        self,
        findings: list[dict[str, object]],
        overall_score: int | None = None,
        tier: str | None = None,
        languages: list[str] | None = None,
        frameworks: list[str] | None = None,
    ) -> dict[str, object] | None:
        url = f"{self.base_url}{self.endpoint}"
        payload = {
            "findings": findings,
            "overall_score": overall_score,
            "tier": tier,
            "languages": languages or [],
            "frameworks": frameworks or [],
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                return dict(response.json())
        except httpx.TimeoutException:
            logger.warning("ai_enrichment_timeout", url=url)
            return None
        except httpx.HTTPStatusError as e:
            logger.warning("ai_enrichment_http_error", status=e.response.status_code, url=url)
            return None
        except Exception as e:
            logger.warning("ai_enrichment_failed", error=str(e), url=url)
            return None
