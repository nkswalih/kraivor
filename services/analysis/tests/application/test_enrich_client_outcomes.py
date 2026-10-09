"""Pin that a transport failure says which transport failure it was.

`AiEnrichmentClient.enrich_findings` returned `dict | None`, and every failure
path returned `None`:

    except httpx.TimeoutException:    ... return None
    except httpx.HTTPStatusError as e: ... return None
    except Exception as e:            ... return None

A timeout, a 500, a 401 and a connection refusal were therefore one event. The
caller could log a single message covering all of them -- and did, literally: "AI
service is unreachable, timing out, or returning errors" -- and no user ever saw
any of it.

That mattered twice over once the summary's reason became storable. The whole
point of the previous commit was that a user looking at a completed run with no
AI summary should be told why. But this client is the *first* thing that has to
answer that question for the most common case of all: the AI service never
answered at all, so there is no `ai_summary_error` in the response to narrow, and
nothing would have been written. The reason column would have been populated only
when the AI service was reachable enough to explain itself.

A request id, forwarded as `X-Request-ID`, is here for the same reason: it is the
difference between a user report that can be matched to a log line and one that
cannot, and the enrichment runs concurrently enough that "the AI summary" is not
a unique thing to go and look for.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import httpx
import pytest

from app.infrastructure.ai import enrichment_client as client_mod
from app.infrastructure.ai.enrichment_client import AiEnrichmentClient

if TYPE_CHECKING:  # pragma: no cover - typing only
    # Under `from __future__ import annotations` the annotations naming this are
    # strings, so the import is never evaluated at runtime and a pre-fix module
    # without the class still collects.
    from app.infrastructure.ai.enrichment_client import EnrichOutcome

pytestmark = pytest.mark.unit

# The header name both services agree on. Read off the module rather than
# imported, so that running this file against pre-fix source produces real test
# failures rather than a collection-time ImportError that would hide every other
# defect in this file behind one error.
#
# `EnrichOutcome` and this constant are both introduced by the fix, and the
# annotations below that name `EnrichOutcome` are strings
# (`from __future__ import annotations`), so they cost nothing at runtime.
_REQUEST_ID_HEADER: str | None = getattr(client_mod, "REQUEST_ID_HEADER", None)


def _request_id_header() -> str:
    if _REQUEST_ID_HEADER is None:  # pragma: no cover - the pre-fix shape
        pytest.fail(
            "the client sends no request id, so a user report of a missing "
            "summary cannot be matched to a line in the AI service's log"
        )
    return _REQUEST_ID_HEADER


class _FakeResponse:
    """Just enough of `httpx.Response` for the client's three failure arms."""

    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"status {self.status_code}",
                request=_REQUEST,
                # `cast` rather than a genuine `httpx.Response`: the client reads
                # only `.status_code` and `.text` off it, and building a real one
                # needs a stream and an encoding to be valid.
                response=cast("httpx.Response", self),
            )

    def json(self) -> dict[str, object]:
        return {"findings": [], "ai_executive_summary": None}


_REQUEST = httpx.Request("POST", "http://ai.internal/v1/analysis/enrich")


def _client() -> AiEnrichmentClient:
    """A client that will not read configuration or open a socket.

    `__new__` rather than `__init__`, which calls `get_settings()`. The six
    attributes below are the whole of the instance state the code under test reads,
    and setting them explicitly means a new attribute added to `__init__` shows up
    here as an obvious gap rather than as a mystery `AttributeError` mid-test.
    """
    stub = AiEnrichmentClient.__new__(AiEnrichmentClient)
    stub.base_url = "http://ai.internal"
    stub.endpoint = "/v1/analysis/enrich"
    stub.timeout = 120
    stub.internal_header_name = "X-Internal-Request"
    stub.internal_secret = "internal-secret"
    return stub


def _patch_client(monkeypatch: pytest.MonkeyPatch, client: object) -> None:
    """Replace `httpx.AsyncClient` as the module under test resolves it.

    By string target rather than through the imported `httpx` module:
    `enrichment_client` does not re-export `httpx`, so attribute access on it is a
    mypy `attr-defined` error, and patching the shared `httpx.AsyncClient` object
    would leak into every other test in the suite if the string target were wrong.

    `client` is a ready instance, wrapped in a factory here. The production code
    writes `httpx.AsyncClient(timeout=self.timeout)` and then `async with`es the
    result, so a bare replacement has to be callable *and* async-context-managed;
    taking a constructed instance keeps every test from having to re-derive that.
    """
    monkeypatch.setattr(
        "app.infrastructure.ai.enrichment_client.httpx.AsyncClient",
        lambda **_kwargs: client,
    )


class _Raising:
    """Stands in for `AsyncClient`, raising out of `post`."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    async def __aenter__(self) -> _Raising:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def post(self, url: str, **kwargs: object) -> _FakeResponse:
        raise self._error


async def _outcome_for(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> EnrichOutcome:
    _patch_client(monkeypatch, _Raising(error))
    return await _client().enrich_findings(findings=[{"title": "t"}])


def _timeout() -> httpx.TimeoutException:
    return httpx.ReadTimeout("timed out")


def _status(code: int, body: str = "") -> httpx.HTTPStatusError:
    # Same `cast` as `_FakeResponse.raise_for_status`; the two are the only places
    # that construct the error, and they are separate because one is driven by a
    # real response object and this one is built directly by a test.
    return httpx.HTTPStatusError(
        f"status {code}",
        request=_REQUEST,
        response=cast("httpx.Response", _FakeResponse(code, body)),
    )


# ======================================================================
# Each transport failure is its own code
# ======================================================================


class TestTheFailureIsIdentified:
    async def test_a_timeout_is_a_timeout(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Distinct from the others because the advice differs. A slow provider is
        # worth retrying; a refused connection or a rejected key is not.
        outcome = await _outcome_for(monkeypatch, _timeout())

        assert outcome.ok is False
        assert outcome.result is None
        assert outcome.error is not None
        assert outcome.error["code"] == "timeout"

    async def test_a_server_error_is_a_provider_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        outcome = await _outcome_for(monkeypatch, _status(503))

        assert outcome.error is not None
        assert outcome.error["code"] == "provider_unavailable"

    async def test_a_refused_request_is_still_a_provider_failure_but_not_retryable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Same code -- it is the AI service failing to serve -- but a 401 will not
        # fix itself, and "try again in 30 seconds" is the wrong instruction for a
        # credential that is wrong now and will be wrong in 30 seconds.
        outcome = await _outcome_for(monkeypatch, _status(401))

        assert outcome.error is not None
        assert outcome.error["code"] == "provider_unavailable"
        assert outcome.error["suggested_action"] == "wait"
        assert outcome.error["retry_after"] == 0

    async def test_a_rejected_request_says_it_was_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The message differs, because "returned an error" and "rejected this
        # request" point an operator at different parts of their setup.
        outcome = await _outcome_for(monkeypatch, _status(400))

        assert outcome.error is not None
        assert "rejected" in str(outcome.error["message"]).lower()

    async def test_a_transport_refusal_is_unreachable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        outcome = await _outcome_for(monkeypatch, httpx.ConnectError("refused"))

        assert outcome.error is not None
        assert outcome.error["code"] == "provider_unreachable"

    async def test_an_unexpected_exception_is_still_an_envelope(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The last arm must not re-raise. Findings enrichment failing must not fail
        # the job -- but it still has to produce a reason, or the reason column is
        # empty for the one case where nothing could be learned about the request.
        outcome = await _outcome_for(monkeypatch, TypeError("unhashable type"))

        assert outcome.ok is False
        assert outcome.error is not None
        assert outcome.error["code"] == "provider_unreachable"

    async def test_the_three_failures_are_not_the_same_value(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The property the whole change exists for, stated as a comparison rather
        # than as three separate assertions. Three assertions on three separate
        # codes would still pass if all three were returning the same envelope and
        # the tests were merely checking each against itself.
        envelopes = []
        for error in (_timeout(), _status(503), httpx.ConnectError("refused")):
            outcome = await _outcome_for(monkeypatch, error)
            assert outcome.error is not None
            envelopes.append(outcome.error["code"])

        assert len(set(envelopes)) == 3, f"collapsed to one value: {envelopes}"


# ======================================================================
# The envelope shape
# ======================================================================


class TestTheEnvelopeIsUsable:
    @pytest.mark.parametrize(
        "error",
        [
            pytest.param(_timeout(), id="timeout"),
            pytest.param(_status(503), id="503"),
            pytest.param(_status(401), id="401"),
            pytest.param(httpx.ConnectError("refused"), id="refused"),
            pytest.param(TypeError("boom"), id="unexpected"),
        ],
    )
    async def test_every_failure_produces_the_four_key_envelope(
        self, monkeypatch: pytest.MonkeyPatch, error: Exception
    ) -> None:
        # The envelope has to be the same four keys the AI service produces, or
        # `_readable_summary_error` narrows one and drops the other and the reason
        # is lost again -- which is the bug this file exists to fix, arriving
        # through the new code rather than the old.
        from app.application.analysis.handler import _readable_summary_error

        outcome = await _outcome_for(monkeypatch, error)

        assert outcome.error is not None
        assert set(outcome.error) == {
            "code",
            "message",
            "suggested_action",
            "retry_after",
        }

        narrowed = _readable_summary_error(outcome.error)
        assert narrowed == outcome.error, "the shape the narrower rejects"

    async def test_no_transport_failure_forwards_the_response_body(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The body is logged, not forwarded. It is the AI service's own error output
        # or a proxy's, and this envelope reaches a column the guide endpoint
        # serves to browsers. A body containing an internal hostname or a snippet
        # of configuration is the kind of thing that appears in one.
        secret_body = "upstream connect error: db://internal-prod:5432/api_key=s3cr3t"

        outcome = await _outcome_for(monkeypatch, _status(500, secret_body))

        assert outcome.error is not None
        assert "s3cr3t" not in str(outcome.error)
        assert "internal-prod" not in str(outcome.error)

    async def test_every_message_says_the_findings_are_unaffected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # These are the user-visible strings. Each one is shown next to a completed
        # run whose findings are all present, so a message that reads as "the
        # analysis failed" would be inaccurate -- and would send someone looking
        # for a problem in their repository rather than in our deployment.
        for error in (_timeout(), _status(503), httpx.ConnectError("refused")):
            outcome = await _outcome_for(monkeypatch, error)
            assert outcome.error is not None
            assert "unaffected" in str(outcome.error["message"]), outcome.error

    async def test_a_retryable_failure_asks_for_a_retry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for error in (_timeout(), _status(503), httpx.ConnectError("refused")):
            outcome = await _outcome_for(monkeypatch, error)
            assert outcome.error is not None
            assert outcome.error["suggested_action"] == "retry"
            assert outcome.error["retry_after"] == 30


# ======================================================================
# The request id
# ======================================================================


class _Capturing:
    """Stands in for `AsyncClient`, recording the headers that went out.

    Module level rather than a class inside each test: the three tests below need
    the same thing, and a locally-defined class closed over each test's own dict
    meant three copies of the same seven lines -- one of which had already drifted
    (the second forgot to record the full header set and reached into it directly).
    """

    def __init__(self, sent: list[dict[str, object]]) -> None:
        self._sent = sent

    async def __aenter__(self) -> _Capturing:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def post(self, url: str, **kwargs: object) -> _FakeResponse:
        self._sent.append(cast("dict[str, object]", kwargs.get("headers", {})))
        raise httpx.ConnectError("refused")


def _capturing(monkeypatch: pytest.MonkeyPatch, sent: list[dict[str, object]]) -> None:
    _patch_client(monkeypatch, _Capturing(sent))


class TestTheRequestIsIdentifiable:
    async def test_a_request_id_is_forwarded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Asserted on the header that went out, not on anything the outcome
        # returns. The id has to reach the AI service for it to identify anything;
        # a field on `EnrichOutcome` that nothing sends would satisfy an assertion
        # written against it.
        sent: list[dict[str, object]] = []
        _capturing(monkeypatch, sent)

        await _client().enrich_findings(findings=[{"title": "t"}])

        assert len(sent) == 1
        request_id = sent[0].get(_request_id_header())
        assert request_id is not None, "the AI service has nothing to log against"
        assert isinstance(request_id, str)
        assert len(request_id) >= 8

    async def test_each_call_gets_a_different_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # One per call, not one per client instance. `AiEnrichmentClient` is
        # constructed per enrichment, so a per-instance id would happen to work
        # today -- and stop working the moment the singleton pattern is introduced,
        # silently, with every concurrent enrichment sharing an id and the header
        # logged twice with the same value.
        sent: list[dict[str, object]] = []
        _capturing(monkeypatch, sent)

        client = _client()
        await client.enrich_findings(findings=[{"title": "t"}])
        await client.enrich_findings(findings=[{"title": "t"}])

        ids = [headers.get(_request_id_header()) for headers in sent]
        assert len(sent) == 2
        assert len(set(ids)) == 2, f"ids repeated: {ids}"

    async def test_the_internal_secret_and_the_id_travel_together(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Belt and braces on a real risk: a header-building change that replaced the
        # dict rather than adding to it would drop the authentication header, and
        # every enrichment would 401 with nothing obviously wrong in the diff.
        sent: list[dict[str, object]] = []
        _capturing(monkeypatch, sent)

        await _client().enrich_findings(findings=[{"title": "t"}])

        assert sent[0]["X-Internal-Request"] == "internal-secret"
        assert sent[0][_request_id_header()]

    def test_the_header_name_is_the_one_the_contract_names(self) -> None:
        # The constant is the contract with the AI service, with every other
        # service that might log this header, and with whoever greps these logs
        # during an incident. Renaming it consistently on both sides keeps the
        # tests green while breaking every one of those, so the literal is pinned
        # here rather than left to whatever the module happens to say.
        assert _request_id_header() == "X-Request-ID"
