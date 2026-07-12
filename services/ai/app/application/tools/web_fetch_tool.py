import aiohttp

from app.application.tools.base import BaseTool


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "Fetch and extract text content from a URL"

    async def run(self, url: str) -> str:
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(url, timeout=aiohttp.ClientTimeout(15)) as resp,
            ):
                text = await resp.text()
                import re

                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                return text[:4000]
        except Exception as e:
            return f"Failed to fetch {url}: {e}"
