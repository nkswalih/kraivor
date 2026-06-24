import ast
import re
from typing import Any

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

    # FastAPI/Flask/Django route decorator patterns
    _ROUTE_DECORATOR_PATTERNS: list[re.Pattern] = [
        re.compile(r"@(?:app|router|bp)\.(?:get|post|put|delete|patch|options)\(['\"]"),
        re.compile(r"@route\(['\"]"),
        re.compile(r"@(?:app|router|bp)\.route\(['\"]"),
        re.compile(r"path\(['\"]"),
        re.compile(r"re_path\(['\"]"),
    ]

    _AUTH_DECORATORS: set[str] = {
        "login_required",
        "auth_required",
        "jwt_required",
        "permission_required",
        "roles_required",
    }

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
            if isinstance(node, ast.FunctionDef):
                parsed.functions.append(self._parse_function(node, content))
                parsed.function_calls.extend(self._extract_calls(node))
            elif isinstance(node, ast.AsyncFunctionDef):
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
        snippet = "\n".join(lines[start:end])

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

    def _parse_class(
        self, node: ast.ClassDef, content: str
    ) -> ParsedClass:
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
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

    def _extract_routes(
        self, tree: ast.AST, content: str
    ) -> list[ParsedRoute]:
        routes: list[ParsedRoute] = []
        lines = content.split("\n")

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Check decorators for route patterns
            for decorator in node.decorator_list:
                decorator_str = self._decorator_to_string(decorator)

                for pattern in self._ROUTE_DECORATOR_PATTERNS:
                    match = pattern.search(decorator_str)
                    if match:
                        # Extract HTTP method and path
                        method = self._extract_method(decorator_str)
                        path = self._extract_path(decorator_str)

                        has_auth = any(
                            auth_dec in decorator_str.lower()
                            for auth_dec in self._AUTH_DECORATORS
                        )
                        # Also check other decorators
                        for d in node.decorator_list:
                            d_str = self._decorator_to_string(d).lower()
                            if any(
                                ad in d_str for ad in self._AUTH_DECORATORS
                            ):
                                has_auth = True

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
                                    self._decorator_name(d)
                                    for d in node.decorator_list
                                ],
                                code=snippet,
                            )
                        )
                        break

        return routes

    @staticmethod
    def _calculate_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Calculate McCabe cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.For,
                    ast.While,
                    ast.ExceptHandler,
                    ast.With,
                    ast.Assert,
                ),
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
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                return True
        return False

    @staticmethod
    def _decorator_name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{node.value.id}.{node.attr}" if hasattr(node.value, "id") else node.attr
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
