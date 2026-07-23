from typing import Protocol


class BaseTool(Protocol):
    name: str
    description: str

    async def run(self, **kwargs) -> str: ...
