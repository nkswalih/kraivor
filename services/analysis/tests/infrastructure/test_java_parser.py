import pytest

from app.infrastructure.parsers.java_parser import JavaParser


@pytest.fixture
def parser() -> JavaParser:
    return JavaParser()


@pytest.mark.asyncio
class TestJavaParser:
    async def test_parse_class(self, parser: JavaParser) -> None:
        content = """
package com.example;

public class UserService {
    public void doWork() { }
}
"""
        result = await parser.parse("test.java", content)
        assert any(c.name == "UserService" for c in result.classes)

    async def test_parse_interface(self, parser: JavaParser) -> None:
        content = """
public interface UserRepository {
    User findById(Long id);
    List<User> findAll();
}
"""
        result = await parser.parse("test.java", content)
        assert any(c.name == "UserRepository" for c in result.classes)
        assert any("interface" in c.decorators for c in result.classes if c.name == "UserRepository")

    async def test_parse_methods(self, parser: JavaParser) -> None:
        content = """
public class Calculator {
    public int add(int a, int b) { return a + b; }
    public int subtract(int a, int b) { return a - b; }
}
"""
        result = await parser.parse("test.java", content)
        names = [f.name for f in result.functions]
        assert "add" in names
        assert "subtract" in names

    async def test_parse_imports(self, parser: JavaParser) -> None:
        content = """
package com.example;

import java.util.List;
import org.springframework.web.bind.annotation.*;
import com.example.service.UserService;
"""
        result = await parser.parse("test.java", content)
        sources = [i.source for i in result.imports]
        assert "java.util.List" in sources
        assert "org.springframework.web.bind.annotation.*" in sources

    async def test_parse_package(self, parser: JavaParser) -> None:
        content = """
package com.example.demo;

public class Test { }
"""
        result = await parser.parse("test.java", content)
        assert any(i.source == "com.example.demo" for i in result.imports)

    async def test_parse_spring_routes(self, parser: JavaParser) -> None:
        content = """
@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping
    public List<User> getAll() { return null; }

    @GetMapping("/{id}")
    public User getById(@PathVariable Long id) { return null; }

    @PostMapping
    public User create(@RequestBody User user) { return null; }

    @PutMapping("/{id}")
    public User update(@PathVariable Long id, @RequestBody User user) { return null; }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable Long id) { }
}
"""
        result = await parser.parse("test.java", content)
        methods = [r.method for r in result.routes]
        paths = [r.path for r in result.routes]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
        assert "/{id}" in paths
        assert "/api/users" not in paths  # @RequestMapping is class-level, not extracted as route

    async def test_parse_annotations(self, parser: JavaParser) -> None:
        content = """
public class App {
    @SuppressWarnings("unchecked")
    public void process() { }
}
"""
        result = await parser.parse("test.java", content)
        assert any("SuppressWarnings" in str(f.decorators) for f in result.functions)

    async def test_calculate_complexity(self, parser: JavaParser) -> None:
        content = """
public class Checker {
    public int check(int a, int b) {
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
        result = await parser.parse("test.java", content)
        func = next(f for f in result.functions if f.name == "check")
        assert func.complexity > 1

    async def test_empty_file(self, parser: JavaParser) -> None:
        result = await parser.parse("empty.java", "")
        assert result.language == "java"
        assert result.lines_count == 0

    async def test_parse_enum(self, parser: JavaParser) -> None:
        content = """
public enum Status {
    ACTIVE,
    INACTIVE,
    PENDING
}
"""
        result = await parser.parse("test.java", content)
        assert any(c.name == "Status" for c in result.classes)

    async def test_parse_record(self, parser: JavaParser) -> None:
        content = """
public record UserDto(Long id, String name, String email) { }
"""
        result = await parser.parse("test.java", content)
        assert any(c.name == "UserDto" for c in result.classes)

    async def test_language_and_extension(self, parser: JavaParser) -> None:
        assert parser.language == "java"
        assert ".java" in parser.supported_extensions

    async def test_parse_class_with_extends_implements(self, parser: JavaParser) -> None:
        content = """
public class UserServiceImpl extends BaseService implements UserService {
    public void execute() { }
}
"""
        result = await parser.parse("test.java", content)
        cls = next(c for c in result.classes if c.name == "UserServiceImpl")
        assert "BaseService" in cls.bases
        assert "UserService" in cls.bases
