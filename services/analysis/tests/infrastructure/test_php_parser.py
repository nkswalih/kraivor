import pytest

from app.infrastructure.parsers.php_parser import PhpParser


@pytest.fixture
def parser() -> PhpParser:
    return PhpParser()


@pytest.mark.asyncio
class TestPhpParser:
    async def test_parse_class(self, parser: PhpParser) -> None:
        content = """
<?php
namespace App\\Service;

class UserService {
    public function doWork() { }
}
"""
        result = await parser.parse("test.php", content)
        assert any(c.name == "UserService" for c in result.classes)

    async def test_parse_interface(self, parser: PhpParser) -> None:
        content = """
<?php
interface UserRepository {
    public function findById($id);
    public function findAll();
}
"""
        result = await parser.parse("test.php", content)
        assert any(c.name == "UserRepository" for c in result.classes)
        assert any("interface" in c.decorators for c in result.classes if c.name == "UserRepository")

    async def test_parse_trait(self, parser: PhpParser) -> None:
        content = """
<?php
trait Loggable {
    public function log($msg) { }
}
"""
        result = await parser.parse("test.php", content)
        assert any(c.name == "Loggable" for c in result.classes)
        assert any("trait" in c.decorators for c in result.classes if c.name == "Loggable")

    async def test_parse_enum(self, parser: PhpParser) -> None:
        content = """
<?php
enum Status: string {
    case ACTIVE = 'active';
    case INACTIVE = 'inactive';
}
"""
        result = await parser.parse("test.php", content)
        assert any(c.name == "Status" for c in result.classes)
        assert any("enum" in c.decorators for c in result.classes if c.name == "Status")

    async def test_parse_namespace(self, parser: PhpParser) -> None:
        content = """<?php
namespace App\\Http\\Controllers;
"""
        result = await parser.parse("test.php", content)
        assert any(i.source == "App\\Http\\Controllers" for i in result.imports)

    async def test_parse_use_imports(self, parser: PhpParser) -> None:
        content = """<?php
use App\\Models\\User;
use Illuminate\\Http\\Request;
"""
        result = await parser.parse("test.php", content)
        sources = [i.source for i in result.imports]
        assert "App\\Models\\User" in sources
        assert "Illuminate\\Http\\Request" in sources

    async def test_parse_functions(self, parser: PhpParser) -> None:
        content = """<?php
function hello() { return 'world'; }
"""
        result = await parser.parse("test.php", content)
        names = [f.name for f in result.functions]
        assert "hello" in names

    async def test_parse_laravel_route(self, parser: PhpParser) -> None:
        content = """<?php
Route::get('/users', [UserController::class, 'index']);
Route::post('/users', [UserController::class, 'store']);
Route::put('/users/{id}', [UserController::class, 'update']);
Route::delete('/users/{id}', [UserController::class, 'destroy']);
"""
        result = await parser.parse("web.php", content)
        methods = [r.method for r in result.routes]
        paths = [r.path for r in result.routes]
        assert "GET" in methods
        assert "POST" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
        assert "/users" in paths
        assert "/users/{id}" in paths

    async def test_parse_symfony_route(self, parser: PhpParser) -> None:
        content = """<?php
#[Route('/api/hello')]
public function hello() { }
"""
        result = await parser.parse("test.php", content)
        assert any(r.path == "/api/hello" for r in result.routes)

    async def test_calculate_complexity(self, parser: PhpParser) -> None:
        content = """<?php
function check($a, $b) {
    if ($a > $b) {
        for ($i = 0; $i < $a; $i++) {
            if ($i % 2 == 0) {
                return $i;
            }
        }
    }
    return 0;
}
"""
        result = await parser.parse("test.php", content)
        func = next(f for f in result.functions if f.name == "check")
        assert func.complexity > 1

    async def test_empty_file(self, parser: PhpParser) -> None:
        result = await parser.parse("empty.php", "")
        assert result.language == "php"
        assert result.lines_count == 0

    async def test_language_and_extension(self, parser: PhpParser) -> None:
        assert parser.language == "php"
        assert ".php" in parser.supported_extensions

    async def test_class_extends(self, parser: PhpParser) -> None:
        content = """<?php
class AdminController extends Controller {
    public function index() { }
}
"""
        result = await parser.parse("test.php", content)
        cls = next(c for c in result.classes if c.name == "AdminController")
        assert "Controller" in cls.bases

    async def test_class_implements(self, parser: PhpParser) -> None:
        content = """<?php
class UserService implements ServiceInterface, Loggable {
    public function execute() { }
}
"""
        result = await parser.parse("test.php", content)
        cls = next(c for c in result.classes if c.name == "UserService")
        assert "ServiceInterface" in cls.bases
