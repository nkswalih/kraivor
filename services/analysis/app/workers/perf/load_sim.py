from app.core.constants import SimulationStatus
from app.core.logging import get_logger
from app.workers.perf.rpm_calculator import PerformanceMetrics

logger = get_logger(__name__)


class SimulationResult:
    def __init__(
        self,
        concurrent_users: int,
        status: str,
        overall_rpm: int,
        error_rate_pct: float,
        bottlenecks: list[str] | None = None,
        endpoints_analysis: list[dict[str, object]] | None = None,
    ) -> None:
        self.concurrent_users = concurrent_users
        self.status = status
        self.overall_rpm = overall_rpm
        self.error_rate_pct = error_rate_pct
        self.bottlenecks = bottlenecks or []
        self.endpoints_analysis = endpoints_analysis or []
        self.exact_breakpoint: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "concurrent_users": self.concurrent_users,
            "status": self.status,
            "overall_rpm": self.overall_rpm,
            "error_rate_pct": self.error_rate_pct,
            "endpoints_analysis": self.endpoints_analysis or [],
            "bottlenecks": self.bottlenecks or [],
        }


class ProductionSimulator:
    DEFAULT_USER_COUNTS = [100, 500, 5000, 50000]

    async def simulate(
        self,
        perf_metrics: PerformanceMetrics,
    ) -> list[SimulationResult]:
        results: list[SimulationResult] = []
        previous_users = 0

        for concurrent_users in self.DEFAULT_USER_COUNTS:
            result = self._simulate_load(perf_metrics, concurrent_users)
            results.append(result)
            if result.status == SimulationStatus.FAILING:
                breakpoint_val = self._find_exact_breakpoint(
                    perf_metrics,
                    previous_users,
                    concurrent_users,
                )
                result.exact_breakpoint = breakpoint_val
                result.bottlenecks = result.bottlenecks or ["system_overload"]
            previous_users = concurrent_users

        return results

    def _simulate_load(
        self,
        metrics: PerformanceMetrics,
        users: int,
    ) -> SimulationResult:
        arrival_rate = users / 60.0
        avg_response_time = self._get_avg_response_time(metrics) / 1000.0
        service_rate = 1.0 / avg_response_time if avg_response_time > 0 else 10.0
        capacity = self._calculate_available_capacity(metrics)

        if capacity <= 0:
            return SimulationResult(
                concurrent_users=users,
                status=SimulationStatus.FAILING,
                overall_rpm=0,
                error_rate_pct=100.0,
                bottlenecks=["no_capacity"],
            )

        utilization = arrival_rate / (capacity * service_rate)

        if utilization >= 1.0:
            return SimulationResult(
                concurrent_users=users,
                status=SimulationStatus.FAILING,
                overall_rpm=0,
                error_rate_pct=100.0,
                bottlenecks=self._find_active_bottlenecks(metrics, users),
            )

        if utilization > 0.8:
            status = SimulationStatus.DEGRADED
        else:
            status = SimulationStatus.STABLE

        estimated_rpm = int(arrival_rate * 60 * min(1.0, (1.0 - utilization) * 2))
        error_rate = max(0.0, (utilization - 0.9) * 100.0) if utilization > 0.9 else 0.0

        endpoints_analysis = []
        for em in metrics.endpoints:
            ep_arrival = users / 60.0 / max(len(metrics.endpoints), 1)
            ep_rpm = int(ep_arrival * 60)
            endpoints_analysis.append(
                {
                    "endpoint": em.endpoint,
                    "method": em.method,
                    "estimated_rpm_under_load": max(ep_rpm, 0),
                    "bottlenecks": em.bottlenecks,
                }
            )

        return SimulationResult(
            concurrent_users=users,
            status=status,
            overall_rpm=estimated_rpm,
            error_rate_pct=round(error_rate, 2),
            bottlenecks=self._find_active_bottlenecks(metrics, users),
            endpoints_analysis=endpoints_analysis,
        )

    def _get_avg_response_time(self, metrics: PerformanceMetrics) -> int:
        if not metrics.endpoints:
            return 50
        return int(
            sum(em.p50_latency_ms for em in metrics.endpoints) / len(metrics.endpoints)
        )

    def _calculate_available_capacity(self, metrics: PerformanceMetrics) -> int:
        base = max(4 - len(metrics.bottlenecks), 1) if metrics.bottlenecks else 4
        return base

    def _find_active_bottlenecks(
        self,
        metrics: PerformanceMetrics,
        users: int,
    ) -> list[str]:
        if not metrics.endpoints:
            return ["unknown"]
        bottleneck_map: dict[str, int] = {}
        for em in metrics.endpoints:
            for b in em.bottlenecks:
                bottleneck_map[b] = bottleneck_map.get(b, 0) + 1
        sorted_bottlenecks = sorted(
            bottleneck_map.items(),
            key=lambda x: -x[1],
        )
        return (
            [b[0] for b in sorted_bottlenecks[:3]]
            if sorted_bottlenecks
            else ["increased_load"]
        )

    def _find_exact_breakpoint(
        self,
        metrics: PerformanceMetrics,
        low: int,
        high: int,
    ) -> int:
        for users in range(low + 1, high):
            arrival_rate = users / 60.0
            avg_response_time = self._get_avg_response_time(metrics) / 1000.0
            service_rate = 1.0 / avg_response_time if avg_response_time > 0 else 10.0
            capacity = self._calculate_available_capacity(metrics)
            if capacity <= 0:
                return users
            utilization = arrival_rate / (capacity * service_rate)
            if utilization >= 1.0:
                return users
        return high
