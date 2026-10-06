"""Route extraction, which used to return nothing at all for Python.

The parser handed `ast.unparse` output to patterns that all anchor on `@`, and
`ast.unparse` does not emit the `@` that introduced a decorator -- so
`@router.get("/items")` reached the matcher as `router.get('/items')` and every
pattern missed. A repository whose Python declared a hundred-plus endpoints
reported zero. Django was a second, independent miss: `path(...)` entries sit in
a module-level `urlpatterns` list and are not decorators at all.

Auth detection is covered here for the same reason. The endpoint count and the
`SEC-NO-AUTH`/`SEC-NO-AUTHZ` findings are produced from the same records, so
extracting routes without teaching the parser that FastAPI authorizes through
`Depends(...)` would have turned a fix for "zero endpoints" into roughly ninety
false "missing authentication" findings.
"""

from __future__ import annotations

import pytest

from app.infrastructure.parsers.python_parser import PythonParser


@pytest.fixture
def parser() -> PythonParser:
    return PythonParser()


FASTAPI_ROUTES = """
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/items")
async def list_items():
    return []


@router.post("/items")
async def create_item():
    return {}


@router.delete("/items/{item_id}")
async def remove_item(item_id: int):
    return {}
"""

DJANGO_URLCONF = """
from django.urls import path, include, re_path

from . import views

urlpatterns = [
    path("articles/", views.article_list, name="article-list"),
    path("articles/<int:pk>/", views.article_detail, name="article-detail"),
    re_path(r"^legacy/(?P<slug>[a-z]+)/$", views.legacy_view, name="legacy"),
    include("other.urls"),
    path("redirect/", views.moved()),
]
"""


@pytest.mark.asyncio
class TestDecoratorRoutes:
    """The `@` prefix, restored at the call site."""

    async def test_fastapi_routes_are_found(
        self, parser: PythonParser
    ) -> None:
        result = await parser.parse("routers.py", FASTAPI_ROUTES)
        assert len(result.routes) == 3

    async def test_paths_and_methods_come_through(
        self, parser: PythonParser
    ) -> None:
        result = await parser.parse("routers.py", FASTAPI_ROUTES)
        found = {(r.method, r.path) for r in result.routes}
        assert ("GET", "/items") in found
        assert ("POST", "/items") in found
        assert ("DELETE", "/items/{item_id}") in found

    async def test_handlers_are_named(self, parser: PythonParser) -> None:
        result = await parser.parse("routers.py", FASTAPI_ROUTES)
        assert {r.handler_name for r in result.routes} == {
            "list_items",
            "create_item",
            "remove_item",
        }

    async def test_decorator_route_carries_its_source(
        self, parser: PythonParser
    ) -> None:
        # `code` is what the security rules read for `code_snippet`; it used to
        # be filled and then looked up under a key that did not exist.
        result = await parser.parse("routers.py", FASTAPI_ROUTES)
        create = next(r for r in result.routes if r.method == "POST")
        assert "async def create_item" in create.code

    async def test_plain_functions_are_not_mistaken_for_routes(
        self, parser: PythonParser
    ) -> None:
        result = await parser.parse(
            "utils.py", "def helper():\n    return 1\n"
        )
        assert result.routes == []


@pytest.mark.asyncio
class TestDjangoUrlPatterns:
    async def test_django_routes_are_found(
        self, parser: PythonParser
    ) -> None:
        result = await parser.parse("urls.py", DJANGO_URLCONF)
        assert len(result.routes) == 4

    async def test_paths_come_through(self, parser: PythonParser) -> None:
        result = await parser.parse("urls.py", DJANGO_URLCONF)
        paths = {r.path for r in result.routes}
        assert "articles/" in paths
        assert "articles/<int:pk>/" in paths
        assert "redirect/" in paths

    async def test_re_path_regex_is_captured(
        self, parser: PythonParser
    ) -> None:
        result = await parser.parse("urls.py", DJANGO_URLCONF)
        legacy = next(r for r in result.routes if "legacy" in r.path)
        assert legacy.path.startswith("^legacy/")

    async def test_include_and_non_string_first_args_are_skipped(
        self, parser: PythonParser
    ) -> None:
        # `include("other.urls")` is not a route, and `views.moved()` carries no
        # literal path -- neither belongs in the endpoint count.
        result = await parser.parse("urls.py", DJANGO_URLCONF)
        assert all("other.urls" not in r.path for r in result.routes)
        assert all(r.path != "" for r in result.routes)

    async def test_line_numbers_point_at_the_call(
        self, parser: PythonParser
    ) -> None:
        result = await parser.parse("urls.py", DJANGO_URLCONF)
        first = next(r for r in result.routes if r.path == "articles/")
        assert first.line_start == 7


@pytest.mark.asyncio
class TestAuthDetection:
    """Auth is what separates a true `SEC-NO-AUTH` hit from a false one."""

    async def test_decorator_auth_is_recognised(
        self, parser: PythonParser
    ) -> None:
        content = """
from flask_login import login_required

@app.route("/account")
@login_required
def account():
    return {}
"""
        result = await parser.parse("routes.py", content)
        assert result.routes[0].has_auth is True

    async def test_auth_decorator_on_a_sibling_decorator_counts(
        self, parser: PythonParser
    ) -> None:
        # The route decorator and the auth decorator are separate entries in
        # `decorator_list`; the matching route pattern is on the first.
        content = """
@app.get("/secrets")
@admin_required
async def secrets():
    return {}
"""
        result = await parser.parse("routes.py", content)
        assert len(result.routes) == 1
        assert result.routes[0].has_auth is True

    async def test_depends_in_the_signature_counts(
        self, parser: PythonParser
    ) -> None:
        content = """
from fastapi import Depends

@router.get("/me")
async def me(user = Depends(get_current_user)):
    return user
"""
        result = await parser.parse("routes.py", content)
        assert result.routes[0].has_auth is True

    async def test_annotated_alias_counts(self, parser: PythonParser) -> None:
        # The `Depends(...)` call lives on the module-level alias, not on the
        # handler, so walking the handler alone finds nothing.
        content = """
from typing import Annotated
from fastapi import Depends

CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]


@router.get("/search")
async def search(user: CurrentUser):
    return user
"""
        result = await parser.parse("routes.py", content)
        assert result.routes[0].has_auth is True

    async def test_unauthenticated_route_stays_false(
        self, parser: PythonParser
    ) -> None:
        content = """
@router.get("/public")
async def public():
    return {}
"""
        result = await parser.parse("routes.py", content)
        assert result.routes[0].has_auth is False

    async def test_non_auth_dependency_does_not_count(
        self, parser: PythonParser
    ) -> None:
        content = """
from fastapi import Depends

@router.get("/settings")
async def settings(db = Depends(get_db), page = Depends(page_size)):
    return {}
"""
        result = await parser.parse("routes.py", content)
        assert result.routes[0].has_auth is False

    async def test_django_handler_without_visible_auth_is_unauthenticated(
        self, parser: PythonParser
    ) -> None:
        # A URLconf cannot show the view's auth -- it lives in another module.
        # Recorded as unauthenticated rather than claimed as protected, because
        # the rule that fires on `has_auth` false is the one describing what is
        # demonstrably in the file.
        content = 'urlpatterns = [path("api/", ApiView.as_view(), name="api")]'
        result = await parser.parse("urls.py", content)
        assert len(result.routes) == 1
        assert result.routes[0].has_auth is False
