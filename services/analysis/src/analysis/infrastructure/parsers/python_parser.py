import ast
import re

from app.domain.contracts.parser import (
    AbstractParser,
    ParsedClass,
    ParsedFile,
    ParsedFunction,
    ParsedImport,
    ParsedRoute,
)


class PythonParser(AbstractParser):
    """Python source code parser using the built-in `ast` module.

    This is the primary parser for Python. It uses the stdlib
    `ast` module which is always available, reliable, and
    requires no native compilation.

    For enhanced parsing (tree-sitter), see PythonTreeSitterParser
    which extends this class.
    """

    language: str = "python"
    supported_extensions: list[str] = [".py", ".pyi", ".pyx"]

    # FastAPI/Flask/Django route decorator patterns.
    #
    # The `@` in each of these is load-bearing and was the reason Python
    # repositories reported zero endpoints: `_decorator_to_string` renders the
    # decorator *expression* through `ast.unparse`, which drops the `@` that
    # introduced it. `@router.get("/items")` therefore unparse to
    # `router.get('/items')`, and every pattern below -- each of which anchors
    # on `@` -- failed to match. Java, Go and C# read their own source text
    # rather than an unparse, which is why the same repository reported
    # endpoints for those languages and none for Python.
    _ROUTE_DECORATOR_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"@(?:app|router|bp)\.(?:get|post|put|delete|patch|options)\(['\"]"),
        re.compile(r"@route\(['\"]"),
        re.compile(r"@(?:app|router|bp)\.route\(['\"]"),
        re.compile(r"path\(['\"]"),
        re.compile(r"re_path\(['\"]"),
    ]

    # Django's `urlpatterns` entries. Not decorators, so they need their own
    # extraction: `path("items/", ItemView.as_view(), name="items")` sits at
    # module level inside a list and never reaches `decorator_list`.
    _DJANGO_ROUTE_CALLS: set[str] = {"path", "re_path", "url"}

    # Dependency-injection auth. `@login_required` is only one of the ways a
    # Python endpoint is protected; FastAPI and Flask-RESTX express it as
    # `Depends(get_current_user)` or `Security(require_api_key)` in the
    # signature, and DRF/Starlette wrap it in `Annotated[..., Depends(...)]`.
    # Reading decorators alone marked every such endpoint unprotected, which
    # turned a fix for "endpoints are reported as zero" into a flood of
    # false "missing authentication" findings.
    _AUTH_DEPENDENCY_NAMES: set[str] = {"Depends", "Security"}
    _AUTH_DEPENDENCY_WORDS: tuple[str, ...] = (
        "user",
        "auth",
        "token",
        "current",
        "credential",
        "permission",
        "role",
        "security",
        "admin",
        "login",
        "session",
        "jwt",
        "oauth",
        "guard",
        "verify",
        "owner",
        "member",
        "protect",
        "scope",
    )

    # Auth decorators. A fixed list of five spellings was too narrow:
    # `admin_required`, `require_admin`, `ensure_authenticated`,
    # `@staff_member_required` and a hundred other real decorators all fell
    # through it, and a decorator that reads as absent auth is reported to the
    # user as a missing-authentication finding on a protected endpoint.
    #
    # The match runs against the decorator's *callee*, never its arguments:
    # `@app.route("/admin/users")` must not read as auth because the word
    # `admin` happens to appear in the URL.
    _AUTH_DECORATORS: set[str] = {
        "login_required",
        "auth_required",
        "jwt_required",
        "permission_required",
        "roles_required",
        "staff_member_required",
        "user_passes_test",
        "authenticated",
        "authorized",
    }
    # Names that gate access, on their own without an auth word they say
    # nothing about auth: `cache_required` and `db_required` are not guards.
    _AUTH_DECORATOR_SUFFIXES: tuple[str, ...] = (
        "_required",
        "_require",
        "_guard",
        "_protect",
        "_protected",
        "_authenticated",
        "_authorized",
        "_only",
    )
    _AUTH_DECORATOR_PREFIXES: tuple[str, ...] = (
        "require_",
        "requires_",
        "ensure_",
        "must_",
        "check_",
    )
    _AUTH_DECORATOR_TOKENS: tuple[str, ...] = (
        "auth",
        "login",
        "jwt",
        "oauth",
        "permission",
        "role",
        "admin",
        "token",
        "session",
        "security",
        "protect",
        "owner",
        "member",
        "scope",
        "guard",
        "credential",
        "user",
        "staff",
        "superuser",
        "apikey",
        "api_key",
    )

    async def parse(self, file_path: str, content: str) -> ParsedFile:
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError as e:
            return ParsedFile(
                path=file_path,
                language=self.language,
                content=content,
                size_bytes=len(content.encode("utf-8")),
                lines_count=content.count("\n") + 1,
                errors=[f"SyntaxError: {e}"],
            )

        parsed = ParsedFile(
            path=file_path,
            language=self.language,
            content=content,
            size_bytes=len(content.encode("utf-8")),
            lines_count=content.count("\n") + 1,
            ast_data={"raw_ast": tree},
        )

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parsed.functions.append(self._parse_function(node, content))
                parsed.function_calls.extend(self._extract_calls(node))
            elif isinstance(node, ast.ClassDef):
                parsed.classes.append(self._parse_class(node, content))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parsed.imports.append(
                        ParsedImport(
                            name=alias.name,
                            alias=alias.asname or "",
                            source="",
                            line=node.lineno,
                            is_from=False,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    parsed.imports.append(
                        ParsedImport(
                            name=alias.name,
                            alias=alias.asname or "",
                            source=node.module or "",
                            line=node.lineno,
                            is_from=True,
                        )
                    )

        parsed.routes = self._extract_routes(tree, content)

        return parsed

    def _parse_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, content: str
    ) -> ParsedFunction:
        lines = content.split("\n")
        start = max(0, node.lineno - 1)
        end = min(len(lines), node.end_lineno or node.lineno)
        "\n".join(lines[start:end])

        return ParsedFunction(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node) or "",
            decorators=[self._decorator_name(d) for d in node.decorator_list],
            complexity=self._calculate_complexity(node),
            calls=self._extract_calls(node),
            has_return=self._has_return(node),
            ast_node=node,
        )

    def _parse_class(self, node: ast.ClassDef, content: str) -> ParsedClass:
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name):
                bases.append(f"{base.value.id}.{base.attr}")

        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)

        return ParsedClass(
            name=node.name,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            bases=bases,
            methods=methods,
            decorators=[self._decorator_name(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node) or "",
            ast_node=node,
        )

    def _extract_routes(self, tree: ast.AST, content: str) -> list[ParsedRoute]:
        routes: list[ParsedRoute] = []
        lines = content.split("\n")
        aliases = self._module_auth_aliases(tree)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Check decorators for route patterns.
            #
            # `ast.unparse` drops the `@` that introduced the decorator, so the
            # character is put back here. Every pattern below anchors on it;
            # without this the search never matched and Python repositories
            # reported zero endpoints while the same source in Java or Go
            # reported theirs.
            for decorator in node.decorator_list:
                decorator_str = "@" + self._decorator_to_string(decorator)

                for pattern in self._ROUTE_DECORATOR_PATTERNS:
                    match = pattern.search(decorator_str)
                    if match:
                        # Extract HTTP method and path
                        method = self._extract_method(decorator_str)
                        path = self._extract_path(decorator_str)

                        has_auth = self._has_auth(node, aliases)

                        start = max(0, node.lineno - 1)
                        end = min(len(lines), node.end_lineno or node.lineno)
                        snippet = "\n".join(lines[start:end])

                        routes.append(
                            ParsedRoute(
                                path=path,
                                method=method,
                                handler_name=node.name,
                                line_start=node.lineno,
                                line_end=node.end_lineno or node.lineno,
                                has_auth=has_auth,
                                decorators=[
                                    self._decorator_name(d) for d in node.decorator_list
                                ],
                                code=snippet,
                            )
                        )
                        break

        routes.extend(self._extract_urlpattern_routes(tree, lines))

        return routes

    # ── Auth detection ────────────────────────────────────────────────────

    @classmethod
    def _module_auth_aliases(cls, tree: ast.AST) -> set[str]:
        """Names bound to an annotation that carries an auth dependency.

        FastAPI and Django Ninja express authentication in a type alias rather
        than in each handler::

            CurrentUser = Annotated[JWTPayload, Depends(get_current_user)]

            async def search(user: CurrentUser): ...

        The `Depends(...)` call lives on the module-level assignment, so walking
        the handler finds nothing and every one of its endpoints reads as
        unprotected. Collecting the alias names first lets the annotation on the
        parameter stand in for the call it expands to.
        """
        aliases: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            if value is None:
                continue
            if not any(cls._call_is_auth_dependency(sub) for sub in ast.walk(value)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    aliases.add(target.id)
        return aliases

    @classmethod
    def _decorator_is_auth(cls, decorator: ast.AST) -> bool:
        """Whether a decorator gates access behind authentication.

        Two rules, both applied to the decorator's *callee* only:

        1. An exact name from `_AUTH_DECORATORS`.
        2. A gating shape -- `*_required`, `require_*`, `ensure_*`,
           `check_*`, `*_only` -- carrying an auth word. `admin_required`
           and `require_admin` both count; `cache_required` and
           `db_required` do not, because a gate without an auth word says
           nothing about auth.

        Arguments are excluded on purpose. `@app.route("/admin/users")` names
        an unauthenticated public route, and matching the whole decorator
        string would read the word `admin` out of the URL and report it as
        protected -- the exact inverse of the bug this code was written to
        fix.
        """
        callee = cls._decorator_name(decorator).lower()
        if not callee:
            return False

        # `auth.login_required` -- match on the final segment.
        leaf = callee.rsplit(".", 1)[-1]
        if leaf in cls._AUTH_DECORATORS or callee in cls._AUTH_DECORATORS:
            return True

        gated = leaf.endswith(cls._AUTH_DECORATOR_SUFFIXES) or leaf.startswith(
            cls._AUTH_DECORATOR_PREFIXES
        )
        if not gated:
            return False
        return any(word in leaf for word in cls._AUTH_DECORATOR_TOKENS)

    @classmethod
    def _has_auth(cls, node: ast.AST, aliases: set[str]) -> bool:
        """Whether an endpoint is protected, by any of the three idioms.

        Decorators (`@login_required`), signature dependencies
        (`Depends(get_current_user)`) and annotation aliases
        (`user: CurrentUser` where `CurrentUser = Annotated[..., Depends(...)]`).
        Checking decorators alone marked every FastAPI endpoint in this
        repository unprotected, which is what turned a fix for "endpoints are
        reported as zero" into a flood of false findings.

        Every decorator on the function counts, not only the one that matched a
        route pattern: `@router.get("/x")` and `@login_required` are separate
        decorators and the auth one is usually the second.
        """
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if cls._decorator_is_auth(decorator):
                    return True

            if aliases:
                annotations: list[ast.AST | None] = [
                    arg.annotation
                    for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
                ]
                if node.args.vararg is not None:
                    annotations.append(node.args.vararg.annotation)
                if node.args.kwarg is not None:
                    annotations.append(node.args.kwarg.annotation)
                for annotation in annotations:
                    if isinstance(annotation, ast.Name) and annotation.id in aliases:
                        return True

        return any(cls._call_is_auth_dependency(sub) for sub in ast.walk(node))

    @classmethod
    def _call_is_auth_dependency(cls, node: ast.AST) -> bool:
        """A `Depends(...)`/`Security(...)` call guarding on an auth concept."""
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (
            func.attr if isinstance(func, ast.Attribute) else ""
        )
        if name not in cls._AUTH_DEPENDENCY_NAMES:
            return False
        if not node.args:
            return False
        target = node.args[0]
        target_name = (
            target.id
            if isinstance(target, ast.Name)
            else target.attr
            if isinstance(target, ast.Attribute)
            else ""
        ).lower()
        return any(w in target_name for w in cls._AUTH_DEPENDENCY_WORDS)

    # ── Django `urlpatterns` ──────────────────────────────────────────────

    @classmethod
    def _extract_urlpattern_routes(
        cls, tree: ast.AST, lines: list[str]
    ) -> list[ParsedRoute]:
        """Routes declared as `path(...)` inside a module-level `urlpatterns`.

        Django does not decorate its views: `ItemView.as_view()` is handed to
        `path()` in a list at module level, so the decorator walk above never
        sees it. That is the other half of the zero-endpoint result -- this
        repository's Django services declare every one of their routes this way.
        """
        routes: list[ParsedRoute] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(
                isinstance(t, ast.Name) and t.id == "urlpatterns" for t in targets
            ):
                continue
            if node.value is None:
                continue

            for call in ast.walk(node.value):
                if not isinstance(call, ast.Call):
                    continue
                func = call.func
                name = func.id if isinstance(func, ast.Name) else (
                    func.attr if isinstance(func, ast.Attribute) else ""
                )
                if name not in cls._DJANGO_ROUTE_CALLS:
                    continue
                if not call.args:
                    continue
                first = call.args[0]
                if not isinstance(first, ast.Constant):
                    continue
                if not isinstance(first.value, str):
                    continue

                handler = ""
                if len(call.args) > 1:
                    handler = ast.unparse(call.args[1])

                # The view's auth lives in another module, so this is a
                # best-effort read of the handler expression itself rather than
                # a claim about the view.
                start = max(0, (call.lineno or 1) - 1)
                end = min(len(lines), call.end_lineno or call.lineno or 1)
                snippet = "\n".join(lines[start:end])

                routes.append(
                    ParsedRoute(
                        path=first.value,
                        method="GET",
                        handler_name=handler,
                        line_start=call.lineno or 1,
                        line_end=call.end_lineno or call.lineno or 1,
                        has_auth=any(
                            w in handler.lower() for w in cls._AUTH_DEPENDENCY_WORDS
                        ),
                        decorators=[],
                        code=snippet,
                    )
                )
        return routes

    @staticmethod
    def _calculate_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Calculate McCabe cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert),
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    @staticmethod
    def _extract_calls(node: ast.AST) -> list[str]:
        calls: list[str] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        return calls

    @staticmethod
    def _has_return(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        return any(isinstance(child, ast.Return) for child in ast.walk(node))

    @staticmethod
    def _decorator_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return (
                f"{node.value.id}.{node.attr}"
                if hasattr(node.value, "id")
                else node.attr
            )
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            if isinstance(node.func, ast.Attribute):
                return node.func.attr
        return str(node)

    @staticmethod
    def _decorator_to_string(node: ast.AST) -> str:
        """Convert a decorator AST node to its string representation."""
        try:
            return ast.unparse(node)
        except Exception:
            return str(node)

    @staticmethod
    def _extract_method(decorator_str: str) -> str:
        """Extract HTTP method from a decorator string."""
        methods = ["get", "post", "put", "delete", "patch", "options"]
        for m in methods:
            if f".{m}(" in decorator_str.lower():
                return m.upper()
        return "GET"

    @staticmethod
    def _extract_path(decorator_str: str) -> str:
        """Extract URL path from a decorator string."""
        match = re.search(r'["\']([^"\']+)["\']', decorator_str)
        return match.group(1) if match else "/"
