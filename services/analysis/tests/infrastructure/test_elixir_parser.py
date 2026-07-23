import pytest

from app.infrastructure.parsers.elixir_parser import ElixirParser


@pytest.fixture
def parser() -> ElixirParser:
    return ElixirParser()


@pytest.mark.asyncio
class TestElixirParser:
    async def test_parse_module(self, parser: ElixirParser) -> None:
        content = """
defmodule MyApp.UserService do
    def hello do
        :world
    end
end
"""
        result = await parser.parse("test.ex", content)
        assert any(c.name == "MyApp.UserService" for c in result.classes)
        assert any(
            "module" in c.decorators
            for c in result.classes
            if c.name == "MyApp.UserService"
        )

    async def test_parse_functions(self, parser: ElixirParser) -> None:
        content = """
defmodule Calculator do
    def add(a, b) do
        a + b
    end

    defp subtract(a, b) do
        a - b
    end
end
"""
        result = await parser.parse("test.ex", content)
        names = [f.name for f in result.functions]
        assert "add" in names
        assert "subtract" in names

    async def test_parse_phoenix_routes(self, parser: ElixirParser) -> None:
        content = """
scope "/api" do
    get "/users", UserController, :index
    post "/users", UserController, :create
    put "/users/:id", UserController, :update
    patch "/users/:id", UserController, :partial
    delete "/users/:id", UserController, :delete
end
"""
        result = await parser.parse("router.ex", content)
        methods = [r.method for r in result.routes]
        paths = [r.path for r in result.routes]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "PATCH" in methods
        assert "DELETE" in methods
        assert "/users" in paths
        assert "/users/:id" in paths

    async def test_parse_phoenix_resources(self, parser: ElixirParser) -> None:
        content = """
scope "/api" do
    resources "/users", UserController
end
"""
        result = await parser.parse("router.ex", content)
        assert any(r.path == "/users" for r in result.routes)
        assert any(r.method == "RESOURCE" for r in result.routes)

    async def test_parse_imports(self, parser: ElixirParser) -> None:
        content = """
alias MyApp.Repo
import Ecto.Query
require Logger
use MyApp.Web, :controller
"""
        result = await parser.parse("test.ex", content)
        sources = [i.source for i in result.imports]
        assert "MyApp.Repo" in sources
        assert "Ecto.Query" in sources
        assert "Logger" in sources
        assert "MyApp.Web" in sources

    async def test_parse_defmacro(self, parser: ElixirParser) -> None:
        content = """
defmodule Helpers do
    defmacro my_if(condition, do: block) do
        quote do
            unquote(condition) && unquote(block)
        end
    end
end
"""
        result = await parser.parse("test.ex", content)
        assert any(f.name == "my_if" for f in result.functions)

    async def test_empty_file(self, parser: ElixirParser) -> None:
        result = await parser.parse("empty.ex", "")
        assert result.language == "elixir"
        assert result.lines_count == 0

    async def test_language_and_extension(self, parser: ElixirParser) -> None:
        assert parser.language == "elixir"
        assert ".ex" in parser.supported_extensions

    async def test_calculate_complexity(self, parser: ElixirParser) -> None:
        content = """
defmodule Checker do
    def check(a, b) do
        if a > b do
            for i <- 0..a do
                if rem(i, 2) == 0 do
                    i
                end
            end
        end
    end
end
"""
        result = await parser.parse("test.ex", content)
        func = next(f for f in result.functions if f.name == "check")
        assert func.complexity > 1
