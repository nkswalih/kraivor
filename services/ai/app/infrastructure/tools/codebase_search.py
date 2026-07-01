from langchain.tools import BaseTool
from app.application.tools.code_search_tool import CodeSearchTool as AppCodeSearchTool


class CodebaseSearchTool(BaseTool):
    name: str = "codebase_search"
    description: str = "Search the indexed codebase by semantic similarity"

    def _run(self, query: str) -> str:
        raise NotImplementedError("Use async version")

    async def _arun(self, query: str) -> str:
        tool = AppCodeSearchTool()
        return await tool.run(query=query)
