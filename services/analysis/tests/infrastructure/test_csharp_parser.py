import pytest

from app.infrastructure.parsers.csharp_parser import CSharpParser


@pytest.fixture
def parser() -> CSharpParser:
    return CSharpParser()


@pytest.mark.asyncio
class TestCSharpParser:
    async def test_parse_class(self, parser: CSharpParser) -> None:
        content = """
using System;

namespace MyApp {
    public class UserService {
        public void DoWork() { }
    }
}
"""
        result = await parser.parse("test.cs", content)
        assert len(result.classes) >= 1
        assert any(c.name == "UserService" for c in result.classes)

    async def test_parse_interface(self, parser: CSharpParser) -> None:
        content = """
public interface IUserRepository {
    User GetById(int id);
}
"""
        result = await parser.parse("test.cs", content)
        assert any(c.name == "IUserRepository" for c in result.classes)
        assert any("interface" in c.decorators for c in result.classes if c.name == "IUserRepository")

    async def test_parse_record(self, parser: CSharpParser) -> None:
        content = 'public record UserDto(string Name, string Email);'
        result = await parser.parse("test.cs", content)
        assert any(c.name == "UserDto" for c in result.classes)

    async def test_parse_methods(self, parser: CSharpParser) -> None:
        content = """
public class Calculator {
    public int Add(int a, int b) { return a + b; }
    public int Subtract(int a, int b) { return a - b; }
}
"""
        result = await parser.parse("test.cs", content)
        names = [f.name for f in result.functions]
        assert "Add" in names
        assert "Subtract" in names

    async def test_parse_using_directives(self, parser: CSharpParser) -> None:
        content = """
using System;
using System.Collections.Generic;
using Microsoft.AspNetCore.Mvc;
"""
        result = await parser.parse("test.cs", content)
        sources = [i.source for i in result.imports]
        assert "System" in sources
        assert "System.Collections.Generic" in sources
        assert "Microsoft.AspNetCore.Mvc" in sources

    async def test_parse_aspnet_route(self, parser: CSharpParser) -> None:
        content = """
[ApiController]
[Route("api/users")]
public class UsersController {
    [HttpGet]
    public IActionResult GetAll() { return Ok(); }

    [HttpGet("{id}")]
    public IActionResult GetById(int id) { return Ok(); }

    [HttpPost]
    public IActionResult Create() { return Ok(); }
}
"""
        result = await parser.parse("test.cs", content)
        methods = [r.method for r in result.routes]
        paths = [r.path for r in result.routes]
        assert "GET" in methods
        assert "POST" in methods
        assert "/" in paths
        assert "{id}" in paths

    async def test_parse_minimal_api_route(self, parser: CSharpParser) -> None:
        content = """
var app = builder.Build();
app.MapGet("/", () => "Hello");
app.MapPost("/users", (User user) => { });
app.MapPut("/users/{id}", (int id, User user) => { });
app.MapDelete("/users/{id}", (int id) => { });
"""
        result = await parser.parse("test.cs", content)
        methods = [r.method for r in result.routes]
        paths = [r.path for r in result.routes]
        assert "MAPGET" in methods
        assert "MAPPOST" in methods
        assert "MAPDELETE" in methods
        assert "/users" in paths
        assert "/users/{id}" in paths

    async def test_parse_properties(self, parser: CSharpParser) -> None:
        content = """
public class Config {
    public string Name { get; set; }
    public int Count { get; set; }
}
"""
        result = await parser.parse("test.cs", content)
        assert any(c.name == "Name" and "property" in c.decorators for c in result.classes)

    async def test_calculate_complexity(self, parser: CSharpParser) -> None:
        content = """
public class Checker {
    public int Check(int a, int b) {
        if (a > b) {
            for (int i = 0; i < a; i++) {
                if (i % 2 == 0) {
                    return i;
                }
            }
        }
        return 0;
    }
}
"""
        result = await parser.parse("test.cs", content)
        func = next(f for f in result.functions if f.name == "Check")
        assert func.complexity > 1

    async def test_empty_file(self, parser: CSharpParser) -> None:
        result = await parser.parse("empty.cs", "")
        assert result.language == "csharp"
        assert result.lines_count == 0

    async def test_parse_struct(self, parser: CSharpParser) -> None:
        content = """
public struct Point {
    public int X { get; set; }
    public int Y { get; set; }
}
"""
        result = await parser.parse("test.cs", content)
        assert any(c.name == "Point" for c in result.classes)

    async def test_parse_generic_method(self, parser: CSharpParser) -> None:
        content = """
public class Repo {
    public T Get<T>(int id) { return default; }
}
"""
        result = await parser.parse("test.cs", content)
        names = [f.name for f in result.functions]
        assert "Get<T>" in names

    async def test_language_and_extension(self, parser: CSharpParser) -> None:
        assert parser.language == "csharp"
        assert ".cs" in parser.supported_extensions
