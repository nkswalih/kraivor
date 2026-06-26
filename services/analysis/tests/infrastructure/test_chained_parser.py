import pytest

from app.infrastructure.parsers import (
    CSharpParser,
    ElixirParser,
    GoParser,
    JavaParser,
    KotlinParser,
    MernParser,
    PhpParser,
    PythonParser,
    RubyParser,
    RustParser,
)
from app.infrastructure.parsers.base import ChainedParser


@pytest.fixture
def chained_parser() -> ChainedParser:
    parser = ChainedParser()
    parser.register(PythonParser())
    parser.register(GoParser())
    parser.register(MernParser())
    parser.register(CSharpParser())
    parser.register(JavaParser())
    parser.register(PhpParser())
    parser.register(RubyParser())
    parser.register(RustParser())
    parser.register(KotlinParser())
    parser.register(ElixirParser())
    return parser


@pytest.mark.asyncio
class TestChainedParser:
    async def test_dispatch_python(self, chained_parser: ChainedParser) -> None:
        content = "def hello(): pass"
        result = await chained_parser.parse("main.py", content)
        assert result.language == "python"

    async def test_dispatch_javascript(self, chained_parser: ChainedParser) -> None:
        content = "function hello() {}"
        result = await chained_parser.parse("app.js", content)
        assert result.language == "javascript"

    async def test_dispatch_typescript(self, chained_parser: ChainedParser) -> None:
        content = "const hello: string = 'world';"
        result = await chained_parser.parse("app.ts", content)
        assert result.language == "javascript"

    async def test_dispatch_go(self, chained_parser: ChainedParser) -> None:
        content = "package main\nfunc main() {}"
        result = await chained_parser.parse("main.go", content)
        assert result.language == "go"

    async def test_dispatch_csharp(self, chained_parser: ChainedParser) -> None:
        content = "using System;\npublic class Foo {}"
        result = await chained_parser.parse("Foo.cs", content)
        assert result.language == "csharp"

    async def test_dispatch_java(self, chained_parser: ChainedParser) -> None:
        content = "package com.example;\npublic class Foo {}"
        result = await chained_parser.parse("Foo.java", content)
        assert result.language == "java"

    async def test_unknown_extension_returns_unknown(self, chained_parser: ChainedParser) -> None:
        content = "some content"
        result = await chained_parser.parse("file.xyz", content)
        assert result.language == "unknown"

    async def test_csharp_parser_extracts_classes(self, chained_parser: ChainedParser) -> None:
        content = """
using System;

public class UserService {
    public void DoWork() { }
}
"""
        result = await chained_parser.parse("UserService.cs", content)
        assert any(c.name == "UserService" for c in result.classes)

    async def test_java_parser_extracts_routes(self, chained_parser: ChainedParser) -> None:
        content = """
@RestController
public class Ctrl {
    @GetMapping("/hello")
    public String hello() { return "hi"; }
}
"""
        result = await chained_parser.parse("Ctrl.java", content)
        assert any(r.path == "/hello" for r in result.routes)
        assert any(r.method == "GET" for r in result.routes)

    async def test_go_parser_extracts_routes(self, chained_parser: ChainedParser) -> None:
        content = """
package main
import "github.com/gin-gonic/gin"
func main() {
    r := gin.Default()
    r.GET("/ping", func(c *gin.Context) { })
}
"""
        result = await chained_parser.parse("main.go", content)
        assert any(r.path == "/ping" for r in result.routes)

    async def test_js_parser_extracts_routes(self, chained_parser: ChainedParser) -> None:
        content = """
const express = require('express');
const router = express.Router();
router.get('/hello', (req, res) => res.json({}));
"""
        result = await chained_parser.parse("routes.js", content)
        assert any(r.path == "/hello" for r in result.routes)

    async def test_python_parser_extracts_functions(self, chained_parser: ChainedParser) -> None:
        content = "def greet(name): return f'Hello {name}'"
        result = await chained_parser.parse("greet.py", content)
        assert any(f.name == "greet" for f in result.functions)

    async def test_dispatch_php(self, chained_parser: ChainedParser) -> None:
        content = "<?php\nclass Foo {}"
        result = await chained_parser.parse("Foo.php", content)
        assert result.language == "php"

    async def test_dispatch_ruby(self, chained_parser: ChainedParser) -> None:
        content = "class Foo\nend"
        result = await chained_parser.parse("Foo.rb", content)
        assert result.language == "ruby"

    async def test_dispatch_rust(self, chained_parser: ChainedParser) -> None:
        content = "struct Foo;"
        result = await chained_parser.parse("Foo.rs", content)
        assert result.language == "rust"

    async def test_dispatch_kotlin(self, chained_parser: ChainedParser) -> None:
        content = "class Foo"
        result = await chained_parser.parse("Foo.kt", content)
        assert result.language == "kotlin"

    async def test_dispatch_elixir(self, chained_parser: ChainedParser) -> None:
        content = "defmodule Foo do\nend"
        result = await chained_parser.parse("Foo.ex", content)
        assert result.language == "elixir"

    async def test_case_insensitive_extension(self, chained_parser: ChainedParser) -> None:
        content = "public class Foo {}"
        result = await chained_parser.parse("Foo.CS", content)
        assert result.language == "csharp"

    async def test_php_parser_extracts_routes(self, chained_parser: ChainedParser) -> None:
        content = """<?php
Route::get('/products', [ProductController::class, 'index']);
"""
        result = await chained_parser.parse("web.php", content)
        assert any(r.path == "/products" for r in result.routes)
        assert any(r.method == "GET" for r in result.routes)

    async def test_ruby_parser_extracts_routes(self, chained_parser: ChainedParser) -> None:
        content = """
Rails.application.routes.draw do
    get '/items' => 'items#index'
end
"""
        result = await chained_parser.parse("routes.rb", content)
        assert any(r.path == "/items" for r in result.routes)

    async def test_elixir_parser_extracts_routes(self, chained_parser: ChainedParser) -> None:
        content = """
scope "/" do
    get "/pages", PageController, :index
end
"""
        result = await chained_parser.parse("router.ex", content)
        assert any(r.path == "/pages" for r in result.routes)
