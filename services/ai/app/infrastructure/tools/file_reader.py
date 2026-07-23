from langchain.tools import BaseTool


class FileReaderTool(BaseTool):
    name: str = "file_reader"
    description: str = "Read contents of a file from the workspace"

    def _run(self, file_path: str) -> str:
        raise NotImplementedError("Use async version")

    async def _arun(self, file_path: str) -> str:
        try:
            import asyncio

            with open(file_path, encoding="utf-8") as f:
                return await asyncio.to_thread(f.read)
        except Exception as e:
            return f"Error reading {file_path}: {e}"
