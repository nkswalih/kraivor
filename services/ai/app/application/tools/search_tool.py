from app.application.tools.base import BaseTool


class DuckDuckGoSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web using DuckDuckGo"

    async def run(self, query: str, max_results: int = 5) -> str:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if not results:
                return "No results found."
            return "\n\n".join(
                f"[{r['title']}]({r['href']})\n{r['body']}" for r in results
            )
        except ImportError:
            return "DuckDuckGo search not available (duckduckgo-search not installed)"
        except Exception as e:
            return f"Search failed: {e}"
