import pytest

from app.infrastructure.parsers.kotlin_parser import KotlinParser


@pytest.fixture
def parser() -> KotlinParser:
    return KotlinParser()


@pytest.mark.asyncio
class TestKotlinParser:
    async def test_parse_class(self, parser: KotlinParser) -> None:
        content = """
package com.example

class UserService {
    fun doWork() { }
}
"""
        result = await parser.parse("test.kt", content)
        assert any(c.name == "UserService" for c in result.classes)

    async def test_parse_interface(self, parser: KotlinParser) -> None:
        content = """
interface UserRepository {
    fun findById(id: Long): User
    fun findAll(): List<User>
}
"""
        result = await parser.parse("test.kt", content)
        assert any(c.name == "UserRepository" for c in result.classes)
        assert any(
            "interface" in c.decorators
            for c in result.classes
            if c.name == "UserRepository"
        )

    async def test_parse_functions(self, parser: KotlinParser) -> None:
        content = """
class App {
    fun greet(name: String): String {
        return "Hello, $name"
    }
    private fun calculate(a: Int, b: Int): Int {
        return a + b
    }
}
"""
        result = await parser.parse("test.kt", content)
        names = [f.name for f in result.functions]
        assert "greet" in names
        assert "calculate" in names

    async def test_parse_imports(self, parser: KotlinParser) -> None:
        content = """
package com.example

import org.springframework.web.bind.annotation.*
import com.example.service.UserService
"""
        result = await parser.parse("test.kt", content)
        sources = [i.source for i in result.imports]
        assert "org.springframework.web.bind.annotation.*" in sources
        assert "com.example.service.UserService" in sources

    async def test_parse_package(self, parser: KotlinParser) -> None:
        content = """
package com.example.demo

class Test { }
"""
        result = await parser.parse("test.kt", content)
        assert any(i.source == "com.example.demo" for i in result.imports)

    async def test_parse_spring_route(self, parser: KotlinParser) -> None:
        content = """
@RestController
class UserController {
    @GetMapping("/users")
    fun getAll(): List<User> = listOf()

    @PostMapping("/users")
    fun create(@RequestBody user: User): User = user
}
"""
        result = await parser.parse("test.kt", content)
        methods = [r.method for r in result.routes]
        paths = [r.path for r in result.routes]
        assert "GET" in methods
        assert "POST" in methods
        assert "/users" in paths

    async def test_parse_ktor_route(self, parser: KotlinParser) -> None:
        content = """
fun Application.module() {
    routing {
        get("/hello") { call.respondText("Hello") }
        post("/data") { call.respondText("OK") }
    }
}
"""
        result = await parser.parse("test.kt", content)
        paths = [r.path for r in result.routes]
        assert "/hello" in paths
        assert "/data" in paths

    async def test_calculate_complexity(self, parser: KotlinParser) -> None:
        content = """
class Checker {
    fun check(a: Int, b: Int): Int {
        if (a > b) {
            for (i in 0 until a) {
                if (i % 2 == 0) {
                    return i
                }
            }
        }
        return 0
    }
}
"""
        result = await parser.parse("test.kt", content)
        names = [f.name for f in result.functions]
        assert "check" in names
        func = next(f for f in result.functions if f.name == "check")
        assert func.complexity > 1

    async def test_empty_file(self, parser: KotlinParser) -> None:
        result = await parser.parse("empty.kt", "")
        assert result.language == "kotlin"
        assert result.lines_count == 0

    async def test_language_and_extension(self, parser: KotlinParser) -> None:
        assert parser.language == "kotlin"
        assert ".kt" in parser.supported_extensions

    async def test_data_class(self, parser: KotlinParser) -> None:
        content = """
data class User(val id: Long, val name: String) {
    fun display() { }
}
"""
        result = await parser.parse("test.kt", content)
        assert any(c.name == "User" for c in result.classes)
