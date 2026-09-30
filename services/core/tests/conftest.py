"""
Test configuration for the workspaces app test suite.

This conftest.py handles the workspaces-specific concern:

1. URL prefix
   The project mounts the workspaces app at a URL prefix defined in the root
   urls.py. In some projects this is /workspace/, in others /api/workspace/.
   We detect it via Django's reverse() and expose it as the `ws_base` fixture
   so test functions use dynamic URLs, not hardcoded strings.

The Celery and DynamoDB isolation fixtures deliberately do NOT live here.
They sit in the service-root conftest.py, because a conftest under `tests/`
applies only to the `tests/` tree — which is exactly the gap that let
`apps/` tests reach for AWS credentials in CI.
"""

import pytest
from django.urls import NoReverseMatch, reverse


@pytest.fixture(scope="session")
def ws_prefix():
    """
    Detect the URL prefix the workspaces app is mounted under.

    Tries to reverse a known workspace URL to discover the prefix.
    Returns the prefix string (e.g. '/workspace' or '/api/workspace').
    Used by ws_url() to build test URLs without hardcoding prefixes.
    """
    try:
        url = reverse("workspace-list")
        # url is e.g. "/workspace/workspaces/" or "/api/workspace/workspaces/"
        # Extract the prefix by stripping the known suffix
        suffix = "/workspaces/"
        if url.endswith(suffix):
            return url[: -len(suffix)]  # e.g. "/workspace" or "/api/workspace"
        return "/workspace"
    except NoReverseMatch:
        # Fallback: assume standard prefix
        return "/workspace"


@pytest.fixture
def ws_url(ws_prefix):
    """
    Factory fixture: returns a URL builder for workspace API paths.

    Usage in tests:
        def test_something(ws_url):
            resp = client.get(ws_url("workspaces/"))
            resp = client.get(ws_url(f"workspaces/{ws_id}/members/"))
    """

    def _build(path: str) -> str:
        # Normalize: strip leading slash from path, add trailing slash if missing
        path = path.strip("/") + "/"
        return f"{ws_prefix}/{path}"

    return _build
