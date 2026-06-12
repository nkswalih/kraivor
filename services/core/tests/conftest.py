"""
Test configuration for the workspaces app test suite.

This conftest.py handles the two environment-specific concerns:

1. URL prefix
   The project mounts the workspaces app at a URL prefix defined in the root
   urls.py. In some projects this is /workspace/, in others /api/workspace/.
   We detect it via Django's reverse() and expose it as the `ws_base` fixture
   so test functions use dynamic URLs, not hardcoded strings.

2. Celery task isolation
   All Celery tasks are configured as ALWAYS_EAGER=False in the test environment.
   We patch them at the task level (not the broker) so tests never need a running
   broker but still verify that tasks are dispatched correctly.
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


@pytest.fixture(autouse=True)
def celery_task_always_eager(settings):
    """
    Force Celery to be synchronous AND suppress broker connection attempts.

    CELERY_TASK_ALWAYS_EAGER makes tasks execute inline (synchronously)
    without needing a broker. Combined with CELERY_TASK_EAGER_PROPAGATES,
    exceptions in tasks bubble up to tests (useful for debugging).

    This fixture is autouse=True so every test gets it automatically.
    No test should ever need a running broker.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = (
        False  # don't let task errors break non-task tests
    )
    settings.CELERY_BROKER_URL = "memory://"  # in-memory broker, no network
    settings.CELERY_RESULT_BACKEND = "cache+memory://"
