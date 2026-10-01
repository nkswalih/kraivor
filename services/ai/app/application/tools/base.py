"""Tool protocol.

Every concrete tool defines its own `run` parameters — `query` for the
search tools, `url` for the fetch tools, `query`/`repo_ids`/`workspace_id`/
`top_k` for code search — and every caller invokes them by keyword.

The protocol therefore declares `*args, **kwargs` rather than keyword-only
`**kwargs`. Keyword-only said the base accepts *zero* positional arguments,
while each override requires `self` plus at least one more, which is an LSP
violation: a caller holding a `BaseTool` could not legally pass an argument
positionally. `*args` makes the base genuinely permissive and matches how the
tools are actually driven.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BaseTool(Protocol):
    name: str
    description: str

    async def run(self, *args: Any, **kwargs: Any) -> str: ...
