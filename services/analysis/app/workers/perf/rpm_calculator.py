import re
from dataclasses import dataclass, field

from app.core.constants import RPM_DEDUCTIONS
from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile, ParsedRoute

logger = get_logger(__name__)

BASE_RPM = 2000


@dataclass
class EndpointMetric:
    endpoint: str
    method: str
    estimated_rpm: int
    p50_latency_ms: int
    p95_latency_ms: int
    p99_latency_ms: int
    max_concurrent_users: int
    bottlenecks: list[str] = field(default_factory=list)
    deductions: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "metric_type": "endpoint",
            "endpoint": self.endpoint,
            "http_method": self.method,
            "estimated_rpm": self.estimated_rpm,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "max_concurrent_users": self.max_concurrent_users,
            "bottleneck_type": ",".join(self.bottlenecks) if self.bottlenecks else None,
            "bottleneck_severity": "high" if self.estimated_rpm < 500 else "medium",
            "bottleneck_detail": "; ".join(
                f"{d['type']}: -{d['rpm_impact']} RPM" for d in self.deductions
            ) if self.deductions else None,
        }


@dataclass
class PerformanceMetrics:
    endpoints: list[EndpointMetric] = field(default_factory=list)
    overall_rpm: int = BASE_RPM
    breaks_at_concurrent_users: int = 10000
    bottlenecks: list[str] = field(default_factory=list)


class RPMCalculator:
    def __init__(self, parsed_files: list[ParsedFile]) -> None:
        self.parsed_files = parsed_files

    async def calculate(self) -> PerformanceMetrics:
        metrics = PerformanceMetrics()
        for pf in self.parsed_files:
            for route in pf.routes:
                endpoint_metric = self._analyze_endpoint(route, pf)
                metrics.endpoints.append(endpoint_metric)
        if metrics.endpoints:
            metrics.overall_rpm = min(
                em.estimated_rpm for em in metrics.endpoints
            )
            metrics.breaks_at_concurrent_users = min(
                em.max_concurrent_users for em in metrics.endpoints
            )
            all_bottlenecks: list[str] = []
            for em in metrics.endpoints:
                all_bottlenecks.extend(em.bottlenecks)
            metrics.bottlenecks = list(set(all_bottlenecks))
        return metrics

    def _analyze_endpoint(self, route: ParsedRoute, pf: ParsedFile) -> EndpointMetric:
        deductions: list[tuple[str, int]] = []
        code = route.code or ""
        full_content = pf.content

        if self._has_n_plus_one(code, full_content):
            deductions.append(("n_plus_one", RPM_DEDUCTIONS["n_plus_one"]))

        sync_calls = self._count_sync_external_calls(code)
        if sync_calls > 0:
            deductions.append(("sync_external_call", RPM_DEDUCTIONS["sync_external_call"] * sync_calls))

        if self._has_unbounded_query(code):
            deductions.append(("unbounded_query", RPM_DEDUCTIONS["unbounded_query"]))

        db_queries = self._count_db_queries(code)
        if db_queries > 5:
            deductions.append(("many_db_queries", RPM_DEDUCTIONS["many_db_queries"] * (db_queries - 5)))

        if self._has_sync_in_async(route, code):
            deductions.append(("sync_in_async", RPM_DEDUCTIONS["sync_in_async"]))

        if self._has_file_io(code):
            deductions.append(("file_io_in_request", RPM_DEDUCTIONS["file_io_in_request"]))

        total_deduction = sum(d[1] for d in deductions)
        rpm = max(BASE_RPM - total_deduction, 50)

        p50 = self._estimate_p50_latency(db_queries, sync_calls, code)
        p95 = int(p50 * 2.5)
        p99 = int(p50 * 5.0)
        breaks_at = self._calculate_breakpoint(rpm, p50)

        return EndpointMetric(
            endpoint=route.path,
            method=route.method,
            estimated_rpm=rpm,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            max_concurrent_users=breaks_at,
            bottlenecks=[d[0] for d in deductions],
            deductions=[{"type": d[0], "rpm_impact": d[1]} for d in deductions],
        )

    def _has_n_plus_one(self, code: str, full_content: str) -> bool:
        target = code or full_content
        loop_pattern = r'for\s+\w+\s+in\s+\w+\s*:'
        query_pattern = r'\.(?:get|filter|all|first|fetch|select)\s*\('
        return bool(re.search(loop_pattern, target)) and bool(re.search(query_pattern, target))

    def _count_sync_external_calls(self, code: str) -> int:
        if not code:
            return 0
        patterns = [
            r'requests\.(?:get|post|put|delete)\(',
            r'urllib\.request\.urlopen\(',
            r'httpx\.(?:get|post|put|delete)\(',
        ]
        count = 0
        for p in patterns:
            count += len(re.findall(p, code))
        return count

    def _has_unbounded_query(self, code: str) -> bool:
        if not code:
            return False
        has_all = bool(re.search(r'\.all\s*\(\)', code))
        has_limit = bool(re.search(r'\.limit\s*\(', code)) or bool(re.search(r':limit\s*=>', code))
        return has_all and not has_limit

    def _count_db_queries(self, code: str) -> int:
        if not code:
            return 0
        patterns = [
            r'\.(?:get|filter|all|first|fetch|select|query|execute)\s*\(',
            r'\.(?:save|create|update|delete|bulk_create)\s*\(',
            r'\.(?:filter|exclude|annotate|aggregate)\s*\(',
        ]
        count = 0
        for p in patterns:
            count += len(re.findall(p, code))
        return count

    def _has_sync_in_async(self, route: ParsedRoute, code: str) -> bool:
        if not code:
            return False
        is_async = bool(re.search(r'async\s+def\s+' + re.escape(route.handler_name), code))
        sync_calls = self._count_sync_external_calls(code)
        return is_async and sync_calls > 0

    def _has_file_io(self, code: str) -> bool:
        if not code:
            return False
        patterns = [
            r'open\s*\(',
            r'\.read\s*\(',
            r'\.write\s*\(',
            r'Path\(',
            r'os\.path\.',
        ]
        return any(re.search(p, code) for p in patterns)

    def _estimate_p50_latency(self, db_queries: int, sync_calls: int, code: str) -> int:
        base = 10
        unindexed = 0
        if code:
            unindexed = len(re.findall(r'\.(?:all|filter)\s*\(', code))
        db_latency = (db_queries - unindexed) * 5 + unindexed * 20
        sync_latency = sync_calls * 50
        return base + db_latency + sync_latency

    def _calculate_breakpoint(self, rpm: int, p50_ms: int) -> int:
        response_time_sec = p50_ms / 1000
        if response_time_sec <= 0:
            return 10000
        breakpoint_val = int(rpm / max(response_time_sec, 0.001))
        return max(min(breakpoint_val, 100000), 1)
