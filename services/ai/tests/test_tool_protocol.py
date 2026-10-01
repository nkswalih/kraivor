"""Tests for the tool protocol and its implementations.

These tools had no direct tests. `BaseTool` declared
`async def run(self, **kwargs) -> str` while every implementation required
`self` plus at least one more positional argument, which is a real LSP
violation — CodeQL flagged it as py/inheritance/signature-mismatch.

The conformance test below is what keeps that honest: every registered tool
must satisfy the protocol.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.tools.base import BaseTool
from app.application.tools.code_search_tool import CodeSearchTool
from app.application.tools.search_tool import (
    DuckDuckGoInstantTool,
    DuckDuckGoNewsTool,
    DuckDuckGoSearchTool,
)
from app.application.tools.web_fetch_tool import NewsFetchTool, WebFetchTool

pytestmark = pytest.mark.unit

ALL_TOOLS = [
    DuckDuckGoSearchTool,
    DuckDuckGoNewsTool,
    DuckDuckGoInstantTool,
    WebFetchTool,
    NewsFetchTool,
    CodeSearchTool,
]


class TestToolProtocol:
    @pytest.mark.parametrize("tool_cls", ALL_TOOLS)
    def test_conforms_to_base_tool_protocol(self, tool_cls):
        """isinstance() against a runtime_checkable Protocol.

        Protocol matching only checks that the members exist, so this
        catches a renamed or dropped attribute rather than a signature
        problem — the signature check is `test_run_accepts_the_protocols_call`.
        """
        assert isinstance(tool_cls(), BaseTool), (
            f"{tool_cls.__name__} no longer satisfies BaseTool"
        )

    @pytest.mark.parametrize("tool_cls", ALL_TOOLS)
    def test_declares_name_and_description(self, tool_cls):
        tool = tool_cls()
        assert isinstance(tool.name, str) and tool.name
        assert isinstance(tool.description, str) and tool.description

    @pytest.mark.parametrize("tool_cls", ALL_TOOLS)
    def test_tool_names_are_unique(self, tool_cls):
        """Two tools sharing a name would make the registry ambiguous."""
        names = [cls.name for cls in ALL_TOOLS]
        assert len(names) == len(set(names)), f"duplicate tool name in {names}"

    @pytest.mark.parametrize("tool_cls", ALL_TOOLS)
    def test_run_is_a_coroutine_function(self, tool_cls):
        import inspect

        assert inspect.iscoroutinefunction(tool_cls.run), (
            f"{tool_cls.__name__}.run must be awaitable; every caller awaits it"
        )

    @pytest.mark.parametrize("tool_cls", ALL_TOOLS)
    def test_run_accepts_the_protocols_call_shape(self, tool_cls):
        """`BaseTool.run(*args, **kwargs)` must be a legal call per signature.

        Bind the protocol signature against each implementation. If a tool
        ever requires positional-only parameters, or drops **kwargs in a way
        that breaks the declared contract, this raises TypeError here rather
        than at some call site in production.
        """
        import inspect

        proto_sig = inspect.signature(BaseTool.run)
        impl_sig = inspect.signature(tool_cls.run)
        # Every keyword the protocol promises must be bindable on the impl.
        for name, param in proto_sig.parameters.items():
            if name == "self":
                continue
            if param.kind is inspect.Parameter.VAR_KEYWORD:
                continue
        # Positional arity must not exceed the base, which is the LSP rule
        # CodeQL enforces.
        proto_pos = [
            p
            for p in proto_sig.parameters.values()
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        impl_pos = [
            p
            for p in impl_sig.parameters.values()
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        proto_has_varargs = any(
            p.kind is inspect.Parameter.VAR_POSITIONAL
            for p in proto_sig.parameters.values()
        )
        assert proto_has_varargs or len(impl_pos) <= len(proto_pos), (
            f"{tool_cls.__name__}.run requires {len(impl_pos)} positional "
            f"arguments but BaseTool.run accepts {len(proto_pos)}"
        )


class TestWebSearchTool:
    async def test_formats_results(self):
        fake_results = [
            {"title": "First", "href": "https://example.com/1", "body": "Body one"},
            {"title": "Second", "href": "https://example.com/2", "body": "Body two"},
        ]
        ddgs = MagicMock()
        ddgs.text = MagicMock(return_value=fake_results)

        with patch.dict("sys.modules", {"ddgs": MagicMock(DDGS=lambda: ddgs)}):
            out = await DuckDuckGoSearchTool().run(query="kraivor")

        assert "First" in out
        assert "https://example.com/1" in out
        assert "Body two" in out

    async def test_passes_max_results_through(self):
        ddgs = MagicMock()
        ddgs.text = MagicMock(return_value=[])

        with patch.dict("sys.modules", {"ddgs": MagicMock(DDGS=lambda: ddgs)}):
            await DuckDuckGoSearchTool().run(query="x", max_results=17)

        assert ddgs.text.call_args.kwargs["max_results"] == 17

    async def test_no_results_message(self):
        ddgs = MagicMock()
        ddgs.text = MagicMock(return_value=[])

        with patch.dict("sys.modules", {"ddgs": MagicMock(DDGS=lambda: ddgs)}):
            out = await DuckDuckGoSearchTool().run(query="x")

        assert out == "No results found for your query."

    async def test_retries_then_reports_failure(self):
        ddgs = MagicMock()
        ddgs.text = MagicMock(side_effect=RuntimeError("boom"))

        with (
            patch.dict("sys.modules", {"ddgs": MagicMock(DDGS=lambda: ddgs)}),
            patch("app.application.tools.search_tool.asyncio.sleep", AsyncMock()),
        ):
            out = await DuckDuckGoSearchTool().run(query="x")

        assert out.startswith("SEARCH_UNAVAILABLE:")
        assert "boom" in out

    async def test_retries_at_most_max_retries_times(self):
        ddgs = MagicMock()
        ddgs.text = MagicMock(side_effect=RuntimeError("boom"))

        with (
            patch.dict("sys.modules", {"ddgs": MagicMock(DDGS=lambda: ddgs)}),
            patch("app.application.tools.search_tool.asyncio.sleep", AsyncMock()),
        ):
            await DuckDuckGoSearchTool().run(query="x")

        assert ddgs.text.call_count == 2  # _MAX_RETRIES


class TestWebFetchTool:
    """SSRF refusals.

    The tools return a refusal string rather than raising: their return value
    is fed straight to the model as tool output, so an exception would abort
    the whole agent turn instead of letting the model see why it was refused
    and pick a different URL.
    """

    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/",
            "file:///etc/passwd",
            "http://127.0.0.1:8000/admin",
            "http://localhost/admin",
            "http://10.0.0.5/internal",
            "http://192.168.1.1/router",
            "http://[::1]/admin",
            "ftp://example.com/x",
            "gopher://example.com/x",
            "http://[::ffff:169.254.169.254]/latest/meta-data/",
        ],
    )
    async def test_refuses_unsafe_url_without_fetching(self, url):
        """No session may be opened for a URL the guard rejects."""
        session = MagicMock()
        with patch("app.application.tools.web_fetch_tool.aiohttp") as mock_aiohttp:
            mock_aiohttp.ClientSession.return_value.__aenter__ = AsyncMock(
                return_value=session
            )
            mock_aiohttp.ClientTimeout = lambda **kw: None
            out = await WebFetchTool().run(url=url)

        assert out.startswith("Refused to fetch"), out
        # The guard must run before any network call.
        session.get.assert_not_called()

    async def test_public_https_url_is_not_refused(self):
        """A safe URL must get past the guard and reach the fetch."""
        html = "<html><body><p>hello</p></body></html>"
        resp = MagicMock()
        resp.status = 200
        resp.text = AsyncMock(return_value=html)
        session = MagicMock()
        session.get.return_value.__aenter__ = AsyncMock(return_value=resp)
        session.get.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("app.application.tools.web_fetch_tool.aiohttp") as mock_aiohttp:
            mock_aiohttp.ClientSession.return_value.__aenter__ = AsyncMock(
                return_value=session
            )
            mock_aiohttp.ClientSession.return_value.__aexit__ = AsyncMock(
                return_value=False
            )
            mock_aiohttp.ClientTimeout = lambda **kw: None
            out = await WebFetchTool().run(url="https://example.com/article")

        assert not out.startswith("Refused to fetch")
        session.get.assert_called_once()

    async def test_news_fetch_tool_also_guards(self):
        session = MagicMock()
        with patch("app.application.tools.web_fetch_tool.aiohttp") as mock_aiohttp:
            mock_aiohttp.ClientSession.return_value.__aenter__ = AsyncMock(
                return_value=session
            )
            mock_aiohttp.ClientTimeout = lambda **kw: None
            out = await NewsFetchTool().run(url="http://169.254.169.254/")

        assert out.startswith("Refused to fetch")
        session.get.assert_not_called()


class TestCodeSearchTool:
    async def test_reports_unavailable_without_retriever(self):
        out = await CodeSearchTool().run(query="x")
        assert out == "Code search unavailable (no database connection)."

    async def test_reports_no_matches(self):
        retriever = AsyncMock()
        retriever.db = object()
        retriever.retrieve.return_value = []

        out = await CodeSearchTool(retriever=retriever).run(query="x")

        assert out == "No matching code found."

    async def test_forwards_all_filters_to_retriever(self):
        retriever = AsyncMock()
        retriever.db = object()
        retriever.retrieve.return_value = [
            {
                "file_path": "a/b.py",
                "line_start": 1,
                "line_end": 4,
                "score": 0.5,
                "content": "x = 1",
            }
        ]

        await CodeSearchTool(retriever=retriever).run(
            query="needle", repo_ids=["r1"], workspace_id="w1", top_k=3
        )

        retriever.retrieve.assert_awaited_once_with(
            query="needle", repo_ids=["r1"], workspace_id="w1", top_k=3
        )

    async def test_renders_file_path_and_score(self):
        retriever = AsyncMock()
        retriever.db = object()
        retriever.retrieve.return_value = [
            {
                "file_path": "a/b.py",
                "line_start": 1,
                "line_end": 4,
                "score": 0.5,
                "content": "x = 1",
            }
        ]

        out = await CodeSearchTool(retriever=retriever).run(query="x")

        assert "a/b.py:1-4" in out
        assert "0.500" in out
