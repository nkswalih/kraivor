"""A redirect must not walk past the outbound URL guard.

`assert_safe_url` only ever sees the URL a caller asks for. If the HTTP
client follows redirects on its own, a public host answers `302` with
`Location: http://169.254.169.254/...` and the *next* request lands on
cloud metadata with no check at all. The response body is then handed to
the model as page text, so this is a full SSRF with the contents read
back.

Every outbound fetcher therefore disables redirect following and
re-validates each hop. These tests drive the real fetchers through fake
transports, so they cover the hop loop rather than the guard alone.
"""

from __future__ import annotations

import aiohttp
import httpx
import pytest
import socket
from app.application.tools.web_fetch_tool import NewsFetchTool, WebFetchTool
from app.core.url_guard import MAX_REDIRECT_HOPS, UnsafeURLError, resolve_redirect
from app.knowledge_engine.multimodal.ingester import MultiModalIngester

METADATA = "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
SECRET = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"

# A public host, as far as the guard is concerned.
REDIRECTOR = "https://redirect.example.com/"
FINAL = "https://final.example.com/page"

HTML = "<html><body><article><p>Real page content.</p></article></body></html>"


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    """Resolve every hostname to a public address, with no network.

    `assert_safe_url` resolves before fetching, so these tests would
    otherwise depend on `redirect.example.com` having a DNS record. The
    literals used for the attack (169.254.169.254, 127.0.0.1) short-circuit
    before DNS, so they are still judged on their own value.
    """

    def fake_getaddrinfo(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


# --------------------------------------------------------------------------
# The policy helper, on its own.
# --------------------------------------------------------------------------


class TestResolveRedirect:
    def test_an_absolute_internal_target_is_refused(self):
        with pytest.raises(UnsafeURLError):
            resolve_redirect(REDIRECTOR, METADATA)

    def test_a_scheme_relative_internal_target_is_refused(self):
        """`//host/path` inherits the scheme, so it is still a real target."""
        with pytest.raises(UnsafeURLError):
            resolve_redirect(REDIRECTOR, "//169.254.169.254/latest/meta-data/")

    def test_a_loopback_target_is_refused(self):
        with pytest.raises(UnsafeURLError):
            resolve_redirect(REDIRECTOR, "http://127.0.0.1:6379/")

    def test_a_file_url_target_is_refused(self):
        with pytest.raises(UnsafeURLError):
            resolve_redirect(REDIRECTOR, "file:///etc/passwd")

    def test_a_relative_public_target_is_allowed(self):
        assert (
            resolve_redirect("https://example.com/a/b", "/c") == "https://example.com/c"
        )

    def test_a_missing_location_is_refused(self):
        with pytest.raises(UnsafeURLError):
            resolve_redirect(REDIRECTOR, None)

    def test_a_blank_location_is_refused(self):
        with pytest.raises(UnsafeURLError):
            resolve_redirect(REDIRECTOR, "   ")


# --------------------------------------------------------------------------
# Fakes.
# --------------------------------------------------------------------------


class _FakeAiohttpResponse:
    """Stands in for an aiohttp response used as an async context manager."""

    def __init__(self, status: int, headers: dict, body: str) -> None:
        self.status = status
        self.headers = headers
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def text(self) -> str:
        return self._body


class _AiohttpRecorder:
    def __init__(self, responses: dict[str, _FakeAiohttpResponse]) -> None:
        self.responses = responses
        self.requested: list[str] = []
        self.kwargs: list[dict] = []

    def install(self, monkeypatch) -> None:
        recorder = self

        def fake_get(self, url, **kwargs):
            url = str(url)
            recorder.requested.append(url)
            recorder.kwargs.append(kwargs)
            return recorder.responses.get(url, _FakeAiohttpResponse(404, {}, ""))

        monkeypatch.setattr(aiohttp.ClientSession, "get", fake_get)


def _aio(responses: dict) -> _AiohttpRecorder:
    return _AiohttpRecorder(
        {
            url: _FakeAiohttpResponse(
                status, {"Location": location} if location else {}, body
            )
            for url, (status, location, body) in responses.items()
        }
    )


def _redirect_to(target: str, body: str = HTML):
    return (302, target, body)


def _ok(body: str = HTML):
    return (200, None, body)


def _patch_httpx(monkeypatch, responses: dict):
    """Route httpx through a mock transport and record every request.

    Returns `(requested_urls, client_kwargs)`.
    """
    requested: list[str] = []
    client_kwargs: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return responses.get(str(request.url), httpx.Response(404, text=""))

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def client_factory(*args, **kw):
        kw["transport"] = transport
        client_kwargs.append(kw)
        return real_client(*args, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    return requested, client_kwargs


# --------------------------------------------------------------------------
# The aiohttp tools, which previously followed redirects freely.
# --------------------------------------------------------------------------


class TestWebFetchRefusesInternalRedirects:
    async def test_a_redirect_to_metadata_is_not_followed(self, monkeypatch):
        recorder = _aio({REDIRECTOR: _redirect_to(METADATA)})
        recorder.install(monkeypatch)

        result = await WebFetchTool().run(REDIRECTOR)

        assert "Refused to follow a redirect" in result
        # The decisive assertion: metadata was never requested.
        assert recorder.requested == [REDIRECTOR]

    async def test_news_fetch_also_refuses_it(self, monkeypatch):
        recorder = _aio({REDIRECTOR: _redirect_to(METADATA)})
        recorder.install(monkeypatch)

        result = await NewsFetchTool().run(REDIRECTOR)

        assert "Refused to follow a redirect" in result
        assert recorder.requested == [REDIRECTOR]

    async def test_the_metadata_body_is_never_returned(self, monkeypatch):
        recorder = _aio({REDIRECTOR: _redirect_to(METADATA), METADATA: _ok(SECRET)})
        recorder.install(monkeypatch)

        result = await WebFetchTool().run(REDIRECTOR)

        assert "AKIAIOSFODNN7EXAMPLE" not in result

    async def test_redirect_following_is_off_on_every_request(self, monkeypatch):
        """The invariant, asserted directly rather than inferred."""
        recorder = _aio({REDIRECTOR: _ok()})
        recorder.install(monkeypatch)

        await WebFetchTool().run(REDIRECTOR)

        assert recorder.kwargs, "no request was made"
        for kwargs in recorder.kwargs:
            assert kwargs.get("allow_redirects") is False

    async def test_a_public_redirect_is_still_followed(self, monkeypatch):
        """Refusing every redirect would break ordinary pages."""
        recorder = _aio({REDIRECTOR: _redirect_to(FINAL), FINAL: _ok()})
        recorder.install(monkeypatch)

        result = await WebFetchTool().run(REDIRECTOR)

        assert "Refused" not in result
        assert recorder.requested == [REDIRECTOR, FINAL]

    async def test_a_relative_public_redirect_is_followed(self, monkeypatch):
        recorder = _aio(
            {
                REDIRECTOR: _redirect_to("/moved"),
                "https://redirect.example.com/moved": _ok(),
            }
        )
        recorder.install(monkeypatch)

        result = await WebFetchTool().run(REDIRECTOR)

        assert "Refused" not in result

    async def test_a_redirect_loop_stops(self, monkeypatch):
        recorder = _aio({REDIRECTOR: _redirect_to(REDIRECTOR)})
        recorder.install(monkeypatch)

        result = await WebFetchTool().run(REDIRECTOR)

        assert "Too many redirects" in result

    async def test_the_hop_count_is_bounded(self, monkeypatch):
        recorder = _aio({REDIRECTOR: _redirect_to(REDIRECTOR)})
        recorder.install(monkeypatch)

        await WebFetchTool().run(REDIRECTOR)

        assert len(recorder.requested) <= MAX_REDIRECT_HOPS + 1

    async def test_the_initial_url_is_still_guarded(self, monkeypatch):
        """Pre-existing behaviour, kept honest."""
        recorder = _aio({"http://169.254.169.254/latest/meta-data/": _ok(SECRET)})
        recorder.install(monkeypatch)

        result = await WebFetchTool().run(METADATA)

        assert "Refused to fetch" in result
        assert recorder.requested == []
        assert "AKIAIOSFODNN7EXAMPLE" not in result


# --------------------------------------------------------------------------
# The httpx ingester, which set follow_redirects=True outright.
# --------------------------------------------------------------------------


class TestIngesterRefusesInternalRedirects:
    async def test_a_redirect_to_metadata_is_not_followed(self, monkeypatch):
        requested = _patch_httpx(
            monkeypatch, {REDIRECTOR: _response(302, location=METADATA)}
        )

        result = await MultiModalIngester().ingest_url(REDIRECTOR)

        assert result.success is False
        assert "Redirect not allowed" in (result.error or "")
        assert requested[0] == [REDIRECTOR]

    async def test_the_metadata_body_is_never_ingested(self, monkeypatch):
        _patch_httpx(
            monkeypatch,
            {
                REDIRECTOR: _response(302, location=METADATA),
                METADATA: _response(200, text=SECRET),
            },
        )

        result = await MultiModalIngester().ingest_url(REDIRECTOR)

        assert "AKIAIOSFODNN7EXAMPLE" not in (result.error or "")

    async def test_redirect_following_is_off_on_every_request(self, monkeypatch):
        _, kwargs = _patch_httpx(monkeypatch, {REDIRECTOR: _response(200)})

        await MultiModalIngester().ingest_url(REDIRECTOR)

        assert kwargs, "no client was constructed"
        for kw in kwargs:
            assert kw.get("follow_redirects") is False

    async def test_a_public_redirect_is_still_followed(self, monkeypatch):
        requested = _patch_httpx(
            monkeypatch,
            {
                REDIRECTOR: _response(301, location=FINAL),
                FINAL: _response(200, text="hello"),
            },
        )

        result = await MultiModalIngester().ingest_url(REDIRECTOR)

        assert "Redirect not allowed" not in (result.error or "")
        assert requested[0] == [REDIRECTOR, FINAL]

    async def test_a_redirect_loop_stops(self, monkeypatch):
        requested = _patch_httpx(
            monkeypatch, {REDIRECTOR: _response(302, location=REDIRECTOR)}
        )

        result = await MultiModalIngester().ingest_url(REDIRECTOR)

        assert "Too many redirects" in (result.error or "")
        assert len(requested[0]) <= MAX_REDIRECT_HOPS + 1


def _response(status: int, *, location: str | None = None, text: str = HTML):
    headers = {"location": location} if location else {}
    return httpx.Response(status, headers=headers, text=text)
