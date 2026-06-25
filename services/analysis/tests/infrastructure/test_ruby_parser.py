import pytest

from app.infrastructure.parsers.ruby_parser import RubyParser


@pytest.fixture
def parser() -> RubyParser:
    return RubyParser()


@pytest.mark.asyncio
class TestRubyParser:
    async def test_parse_class(self, parser: RubyParser) -> None:
        content = """
class UserService
    def do_work
    end
end
"""
        result = await parser.parse("test.rb", content)
        assert any(c.name == "UserService" for c in result.classes)

    async def test_parse_module(self, parser: RubyParser) -> None:
        content = """
module Api
    module V1
    end
end
"""
        result = await parser.parse("test.rb", content)
        assert any(c.name == "Api" for c in result.classes)
        assert any("module" in c.decorators for c in result.classes if c.name == "Api")

    async def test_parse_methods(self, parser: RubyParser) -> None:
        content = """
class Calculator
    def add(a, b)
        a + b
    end
    def subtract(a, b)
        a - b
    end
end
"""
        result = await parser.parse("test.rb", content)
        names = [f.name for f in result.functions]
        assert "add" in names
        assert "subtract" in names

    async def test_parse_requires(self, parser: RubyParser) -> None:
        content = """
require 'json'
require_relative 'config'
"""
        result = await parser.parse("test.rb", content)
        sources = [i.source for i in result.imports]
        assert "json" in sources
        assert "config" in sources

    async def test_parse_rails_route_hash(self, parser: RubyParser) -> None:
        content = """
Rails.application.routes.draw do
    get '/users' => 'users#index'
    post '/users' => 'users#create'
    put '/users/:id' => 'users#update'
    delete '/users/:id' => 'users#destroy'
end
"""
        result = await parser.parse("routes.rb", content)
        methods = [r.method for r in result.routes]
        paths = [r.path for r in result.routes]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
        assert "/users" in paths
        assert "/users/:id" in paths

    async def test_parse_rails_route_block(self, parser: RubyParser) -> None:
        content = """
Rails.application.routes.draw do
    get '/hello', to: 'pages#hello'
    post '/data', controller: 'data'
end
"""
        result = await parser.parse("routes.rb", content)
        paths = [r.path for r in result.routes]
        assert "/hello" in paths
        assert "/data" in paths

    async def test_class_inheritance(self, parser: RubyParser) -> None:
        content = """
class AdminController < ApplicationController
    def index
    end
end
"""
        result = await parser.parse("test.rb", content)
        cls = next(c for c in result.classes if c.name == "AdminController")
        assert "ApplicationController" in cls.bases

    async def test_empty_file(self, parser: RubyParser) -> None:
        result = await parser.parse("empty.rb", "")
        assert result.language == "ruby"
        assert result.lines_count == 0

    async def test_language_and_extension(self, parser: RubyParser) -> None:
        assert parser.language == "ruby"
        assert ".rb" in parser.supported_extensions
