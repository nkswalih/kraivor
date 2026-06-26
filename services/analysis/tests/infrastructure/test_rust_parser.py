import pytest

from app.infrastructure.parsers.rust_parser import RustParser


@pytest.fixture
def parser() -> RustParser:
    return RustParser()


@pytest.mark.asyncio
class TestRustParser:
    async def test_parse_struct(self, parser: RustParser) -> None:
        content = """
pub struct User {
    pub name: String,
    pub email: String,
}
"""
        result = await parser.parse("test.rs", content)
        assert any(c.name == "User" for c in result.classes)
        assert any("struct" in c.decorators for c in result.classes if c.name == "User")

    async def test_parse_enum(self, parser: RustParser) -> None:
        content = """
pub enum Status {
    Active,
    Inactive,
    Pending,
}
"""
        result = await parser.parse("test.rs", content)
        assert any(c.name == "Status" for c in result.classes)
        assert any("enum" in c.decorators for c in result.classes if c.name == "Status")

    async def test_parse_trait(self, parser: RustParser) -> None:
        content = """
pub trait Repository {
    fn find_all(&self) -> Vec<User>;
    fn save(&self, user: User);
}
"""
        result = await parser.parse("test.rs", content)
        assert any(c.name == "Repository" for c in result.classes)
        assert any("trait" in c.decorators for c in result.classes if c.name == "Repository")

    async def test_parse_function(self, parser: RustParser) -> None:
        content = """
pub fn greet(name: &str) -> String {
    format!("Hello, {}!", name)
}

fn calculate(a: i32, b: i32) -> i32 {
    a + b
}
"""
        result = await parser.parse("test.rs", content)
        names = [f.name for f in result.functions]
        assert "greet" in names
        assert "calculate" in names

    async def test_parse_impl_block(self, parser: RustParser) -> None:
        content = """
struct User {}

impl User {
    fn new(name: String) -> Self {
        User {}
    }
    fn greet(&self) -> String {
        String::from("Hello")
    }
}
"""
        result = await parser.parse("test.rs", content)
        assert any(c.name == "User" for c in result.classes)

    async def test_parse_imports(self, parser: RustParser) -> None:
        content = """
use std::collections::HashMap;
use serde::{Deserialize, Serialize};
use tokio::time;
"""
        result = await parser.parse("test.rs", content)
        assert any("std::collections::HashMap" in i.source for i in result.imports)

    async def test_calculate_complexity(self, parser: RustParser) -> None:
        content = """
fn check(a: i32, b: i32) -> i32 {
    if a > b {
        for i in 0..a {
            if i % 2 == 0 {
                return i;
            }
        }
    }
    0
}
"""
        result = await parser.parse("test.rs", content)
        func = next(f for f in result.functions if f.name == "check")
        assert func.complexity > 1

    async def test_empty_file(self, parser: RustParser) -> None:
        result = await parser.parse("empty.rs", "")
        assert result.language == "rust"
        assert result.lines_count == 0

    async def test_language_and_extension(self, parser: RustParser) -> None:
        assert parser.language == "rust"
        assert ".rs" in parser.supported_extensions

    async def test_unit_struct(self, parser: RustParser) -> None:
        content = "pub struct Point;"
        result = await parser.parse("test.rs", content)
        assert any(c.name == "Point" for c in result.classes)
