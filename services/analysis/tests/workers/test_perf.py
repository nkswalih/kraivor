
from app.domain.contracts.parser import ParsedFile, ParsedRoute
from app.workers.perf.rpm_calculator import RPMCalculator


def _make_pf(path: str, content: str = "", routes: list[ParsedRoute] | None = None) -> ParsedFile:
    return ParsedFile(
        path=path,
        language="python",
        content=content,
        size_bytes=len(content),
        lines_count=len(content.split("\n")),
        routes=routes or [],
    )


class TestRPMCalculator:
    async def test_no_endpoints_default_rpm(self) -> None:
        pf = _make_pf("app.py", "")
        calculator = RPMCalculator([pf])
        metrics = await calculator.calculate()
        assert metrics.overall_rpm == 2000
        assert len(metrics.endpoints) == 0

    async def test_clean_endpoint_full_rpm(self) -> None:
        route = ParsedRoute(
            path="/api/health", method="GET", handler_name="health",
            line_start=1, line_end=3,
            code="def health():\n    return {'ok': True}\n",
        )
        pf = _make_pf("routes.py", routes=[route])
        calculator = RPMCalculator([pf])
        metrics = await calculator.calculate()
        assert len(metrics.endpoints) == 1
        assert metrics.endpoints[0].estimated_rpm == 2000
        assert metrics.endpoints[0].bottlenecks == []

    async def test_n_plus_one_deduction(self) -> None:
        route = ParsedRoute(
            path="/api/users", method="GET", handler_name="get_users",
            line_start=1, line_end=5,
            code="def get_users():\n    users = User.all()\n    for u in users:\n        u.profile.get()\n",
        )
        pf = _make_pf("routes.py", routes=[route])
        calculator = RPMCalculator([pf])
        metrics = await calculator.calculate()
        ep = metrics.endpoints[0]
        assert ep.estimated_rpm < 2000
        assert "n_plus_one" in ep.bottlenecks

    async def test_sync_external_call_deduction(self) -> None:
        route = ParsedRoute(
            path="/api/data", method="GET", handler_name="get_data",
            line_start=1, line_end=3,
            code="def get_data():\n    resp = requests.get('https://api.example.com')\n    return resp.json()\n",
        )
        pf = _make_pf("routes.py", routes=[route])
        calculator = RPMCalculator([pf])
        metrics = await calculator.calculate()
        ep = metrics.endpoints[0]
        assert ep.estimated_rpm <= 1800
        assert "sync_external_call" in ep.bottlenecks

    async def test_unbounded_query_deduction(self) -> None:
        route = ParsedRoute(
            path="/api/items", method="GET", handler_name="get_items",
            line_start=1, line_end=3,
            code="def get_items():\n    items = Item.all()\n    return items\n",
        )
        pf = _make_pf("routes.py", routes=[route])
        calculator = RPMCalculator([pf])
        metrics = await calculator.calculate()
        ep = metrics.endpoints[0]
        assert ep.estimated_rpm <= 1700
        assert "unbounded_query" in ep.bottlenecks

    async def test_multiple_endpoints_system_rpm_min(self) -> None:
        routes = [
            ParsedRoute(
                path="/api/fast", method="GET", handler_name="fast",
                line_start=1, line_end=2, code="def fast():\n    return 'ok'\n",
            ),
            ParsedRoute(
                path="/api/slow", method="GET", handler_name="slow",
                line_start=4, line_end=6,
                code="def slow():\n    resp = requests.get('https://api.example.com')\n    Item.all()\n    return resp\n",
            ),
        ]
        pf = _make_pf("routes.py", routes=routes)
        calculator = RPMCalculator([pf])
        metrics = await calculator.calculate()
        assert metrics.overall_rpm == metrics.endpoints[1].estimated_rpm
        assert len(metrics.bottlenecks) >= 1

    async def test_p50_latency_estimate(self) -> None:
        route = ParsedRoute(
            path="/api/test", method="GET", handler_name="test",
            line_start=1, line_end=2, code="def test():\n    return 'ok'\n",
        )
        pf = _make_pf("routes.py", routes=[route])
        calculator = RPMCalculator([pf])
        metrics = await calculator.calculate()
        ep = metrics.endpoints[0]
        assert ep.p50_latency_ms >= 10
        assert ep.p95_latency_ms >= ep.p50_latency_ms
        assert ep.p99_latency_ms >= ep.p95_latency_ms

    async def test_breakpoint_calculation(self) -> None:
        route = ParsedRoute(
            path="/api/test", method="GET", handler_name="test",
            line_start=1, line_end=2, code="def test():\n    return 'ok'\n",
        )
        pf = _make_pf("routes.py", routes=[route])
        calculator = RPMCalculator([pf])
        metrics = await calculator.calculate()
        assert 0 < metrics.endpoints[0].max_concurrent_users <= 100000

    async def test_sync_in_async_detection(self) -> None:
        route = ParsedRoute(
            path="/api/data", method="GET", handler_name="get_data",
            line_start=1, line_end=4,
            code="async def get_data():\n    resp = requests.get('https://api.example.com')\n    return resp.json()\n",
        )
        pf = _make_pf("routes.py", routes=[route])
        calculator = RPMCalculator([pf])
        metrics = await calculator.calculate()
        ep = metrics.endpoints[0]
        assert "sync_in_async" in ep.bottlenecks
