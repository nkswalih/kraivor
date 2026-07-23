"""Web search and fetch tools - unified interface."""

from app.application.tools.search_tool import (
    DuckDuckGoInstantTool,
    DuckDuckGoNewsTool,
    DuckDuckGoSearchTool,
)
from app.application.tools.web_fetch_tool import NewsFetchTool, WebFetchTool


class WebSearchTool:
    async def search(self, query: str, max_results: int = 5) -> str:
        tool = DuckDuckGoSearchTool()
        return await tool.run(query=query, max_results=max_results)

    async def search_news(self, query: str, max_results: int = 5, timelimit: str = "d") -> str:
        tool = DuckDuckGoNewsTool()
        return await tool.run(query=query, max_results=max_results, timelimit=timelimit)

    async def search_instant(self, query: str) -> str:
        tool = DuckDuckGoInstantTool()
        return await tool.run(query=query)

    async def fetch(self, url: str) -> str:
        tool = WebFetchTool()
        return await tool.run(url=url)

    async def fetch_news(self, url: str) -> str:
        tool = NewsFetchTool()
        return await tool.run(url=url)
