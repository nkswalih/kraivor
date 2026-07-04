from app.core.constants import SimulationStatus
from app.workers.perf.load_sim import ProductionSimulator
from app.workers.perf.rpm_calculator import EndpointMetric, PerformanceMetrics


class TestProductionSimulator:
    async def test_stable_at_low_load(self) -> None:
        metrics = PerformanceMetrics(
            endpoints=[
                EndpointMetric(
                    endpoint="/api/health",
                    method="GET",
                    estimated_rpm=2000,
                    p50_latency_ms=10,
                    p95_latency_ms=25,
                    p99_latency_ms=50,
                    max_concurrent_users=10000,
                ),
            ],
            overall_rpm=2000,
            breaks_at_concurrent_users=10000,
        )
        simulator = ProductionSimulator()
        results = await simulator.simulate(metrics)
        assert len(results) == 4
        assert results[0].status == SimulationStatus.STABLE
        assert results[0].concurrent_users == 100

    async def test_degraded_at_medium_load(self) -> None:
        metrics = PerformanceMetrics(
            endpoints=[
                EndpointMetric(
                    endpoint="/api/slow",
                    method="GET",
                    estimated_rpm=100,
                    p50_latency_ms=300,
                    p95_latency_ms=500,
                    p99_latency_ms=1000,
                    max_concurrent_users=500,
                    bottlenecks=["n_plus_one"],
                ),
            ],
            overall_rpm=100,
            breaks_at_concurrent_users=500,
            bottlenecks=["n_plus_one"],
        )
        simulator = ProductionSimulator()
        results = await simulator.simulate(metrics)
        degraded = [r for r in results if r.status == SimulationStatus.DEGRADED]
        assert len(degraded) >= 1

    async def test_failing_at_high_load(self) -> None:
        metrics = PerformanceMetrics(
            endpoints=[
                EndpointMetric(
                    endpoint="/api/slow",
                    method="GET",
                    estimated_rpm=50,
                    p50_latency_ms=1000,
                    p95_latency_ms=2500,
                    p99_latency_ms=5000,
                    max_concurrent_users=100,
                    bottlenecks=["n_plus_one", "sync_external_call"],
                ),
            ],
            overall_rpm=50,
            breaks_at_concurrent_users=100,
            bottlenecks=["n_plus_one", "sync_external_call"],
        )
        simulator = ProductionSimulator()
        results = await simulator.simulate(metrics)
        failing = [r for r in results if r.status == SimulationStatus.FAILING]
        assert len(failing) >= 1

    async def test_empty_metrics_returns_results(self) -> None:
        metrics = PerformanceMetrics()
        simulator = ProductionSimulator()
        results = await simulator.simulate(metrics)
        assert len(results) == 4

    async def test_error_rate_increases_with_load(self) -> None:
        metrics = PerformanceMetrics(
            endpoints=[
                EndpointMetric(
                    endpoint="/api/test",
                    method="GET",
                    estimated_rpm=500,
                    p50_latency_ms=100,
                    p95_latency_ms=250,
                    p99_latency_ms=500,
                    max_concurrent_users=2000,
                    bottlenecks=["many_db_queries"],
                ),
            ],
            overall_rpm=500,
            breaks_at_concurrent_users=2000,
        )
        simulator = ProductionSimulator()
        results = await simulator.simulate(metrics)
        error_rates = [r.error_rate_pct for r in results]
        for i in range(1, len(error_rates)):
            assert error_rates[i] >= error_rates[i - 1]

    async def test_bottlenecks_propagate(self) -> None:
        metrics = PerformanceMetrics(
            endpoints=[
                EndpointMetric(
                    endpoint="/api/test",
                    method="GET",
                    estimated_rpm=300,
                    p50_latency_ms=150,
                    p95_latency_ms=375,
                    p99_latency_ms=750,
                    max_concurrent_users=500,
                    bottlenecks=["sync_external_call", "n_plus_one"],
                ),
            ],
            overall_rpm=300,
            breaks_at_concurrent_users=500,
        )
        simulator = ProductionSimulator()
        results = await simulator.simulate(metrics)
        for r in results:
            if r.bottlenecks:
                assert (
                    "n_plus_one" in r.bottlenecks
                    or "sync_external_call" in r.bottlenecks
                    or "increased_load" in r.bottlenecks
                )

    async def test_endpoints_analysis_included(self) -> None:
        metrics = PerformanceMetrics(
            endpoints=[
                EndpointMetric(
                    endpoint="/api/test",
                    method="GET",
                    estimated_rpm=2000,
                    p50_latency_ms=10,
                    p95_latency_ms=25,
                    p99_latency_ms=50,
                    max_concurrent_users=10000,
                ),
            ],
        )
        simulator = ProductionSimulator()
        results = await simulator.simulate(metrics)
        for r in results:
            if r.endpoints_analysis:
                assert len(r.endpoints_analysis) == 1
                assert r.endpoints_analysis[0]["endpoint"] == "/api/test"
