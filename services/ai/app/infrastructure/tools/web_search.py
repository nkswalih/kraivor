from app.application.tools.search_tool import DuckDuckGoSearchTool
from app.application.tools.web_fetch_tool import WebFetchTool


class WebSearchTool:
    async def search(self, query: str, max_results: int = 5) -> str:
        tool = DuckDuckGoSearchTool()
        return await tool.run(query=query, max_results=max_results)

    async def fetch(self, url: str) -> str:
        tool = WebFetchTool()
        return await tool.run(url=url)
