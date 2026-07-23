import re
from dataclasses import dataclass, field

from app.core.constants import RPM_DEDUCTIONS
from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile, ParsedRoute

logger = get_logger(__name__)

LATENCY_BASE_MS = 10


def _calibrate_base_rpm(parsed_files: list[ParsedFile]) -> int:
    total_files = len(parsed_files)
    if total_files == 0:
        return 500
    total_routes = sum(len(pf.routes) for pf in parsed_files)
    route_boost = max(200, total_routes * 50)
    file_boost = max(300, total_files * 30)
    return min(8000, max(2000, file_boost + route_boost))


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
    confidence: float = 0.8

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
            "bottleneck_detail": (
                "; ".join(
                    f"{d['type']}: -{d['rpm_impact']} RPM" for d in self.deductions
                )
                if self.deductions
                else None
            ),
            "confidence": self.confidence,
        }


@dataclass
class PerformanceMetrics:
    endpoints: list[EndpointMetric] = field(default_factory=list)
    overall_rpm: int = 2000
    breaks_at_concurrent_users: int = 10000
    bottlenecks: list[str] = field(default_factory=list)
    overall_confidence: float = 0.8


class RPMCalculator:
    def __init__(self, parsed_files: list[ParsedFile]) -> None:
        self.parsed_files = parsed_files

    async def calculate(self) -> PerformanceMetrics:
        base_rpm = _calibrate_base_rpm(self.parsed_files)
        metrics = PerformanceMetrics()
        for pf in self.parsed_files:
            for route in pf.routes:
                endpoint_metric = self._analyze_endpoint(route, pf, base_rpm)
                metrics.endpoints.append(endpoint_metric)
        if metrics.endpoints:
            metrics.overall_rpm = min(em.estimated_rpm for em in metrics.endpoints)
            metrics.breaks_at_concurrent_users = min(
                em.max_concurrent_users for em in metrics.endpoints
            )
            metrics.overall_confidence = min(em.confidence for em in metrics.endpoints)
            all_bottlenecks: list[str] = []
            for em in metrics.endpoints:
                all_bottlenecks.extend(em.bottlenecks)
            metrics.bottlenecks = list(set(all_bottlenecks))
        return metrics

    def _analyze_endpoint(
        self, route: ParsedRoute, pf: ParsedFile, base_rpm: int = 2000
    ) -> EndpointMetric:
        deductions: list[tuple[str, int]] = []
        code = route.code or ""
        full_content = pf.content

        if self._has_n_plus_one(code, full_content):
            deductions.append(("n_plus_one", RPM_DEDUCTIONS["n_plus_one"]))

        sync_calls = self._count_sync_external_calls(code)
        if sync_calls > 0:
            deductions.append(
                (
                    "sync_external_call",
                    RPM_DEDUCTIONS["sync_external_call"] * sync_calls,
                )
            )

        if self._has_unbounded_query(code):
            deductions.append(("unbounded_query", RPM_DEDUCTIONS["unbounded_query"]))

        db_queries = self._count_db_queries(code)
        if db_queries > 5:
            deductions.append(
                (
                    "many_db_queries",
                    RPM_DEDUCTIONS["many_db_queries"] * (db_queries - 5),
                )
            )

        if self._has_sync_in_async(route, code):
            deductions.append(("sync_in_async", RPM_DEDUCTIONS["sync_in_async"]))

        if self._has_file_io(code):
            deductions.append(
                ("file_io_in_request", RPM_DEDUCTIONS["file_io_in_request"])
            )

        # New detections
        if self._has_high_cpu_complexity(code):
            deductions.append(("high_complexity", RPM_DEDUCTIONS["high_complexity"]))

        if self._has_memory_pressure(code):
            deductions.append(("memory_pressure", self._memory_pressure_impact(code)))

        serialization = self._count_serialization(code)
        if serialization > 0:
            deductions.append(
                (
                    "serialization_bottleneck",
                    RPM_DEDUCTIONS["serialization_bottleneck"] * serialization,
                )
            )

        if self._has_no_caching(code):
            deductions.append(("no_caching", RPM_DEDUCTIONS["no_caching"]))

        loop_score = self._loop_complexity(code)
        if loop_score > 1:
            deductions.append(("loop_complexity", 100 * (loop_score - 1)))

        total_deduction = sum(d[1] for d in deductions)
        rpm = max(base_rpm - total_deduction, 50)

        p50 = self._estimate_p50_latency(db_queries, sync_calls, code, loop_score)
        p95 = int(p50 * 2.5)
        p99 = int(p50 * 5.0)
        breaks_at = self._calculate_breakpoint(rpm, p50)

        has_route_code = bool(route.code and len(route.code.strip()) > 0)
        has_content = bool(pf.content and len(pf.content.strip()) > 0)
        signal_count = len(
            [d for d, _ in deductions if d not in ("no_caching", "memory_pressure")]
        )
        confidence = self._compute_confidence(
            has_route_code, has_content, db_queries, sync_calls, signal_count
        )

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
            confidence=confidence,
        )

    def _compute_confidence(
        self,
        has_code: bool,
        has_content: bool,
        db_queries: int,
        sync_calls: int,
        signals: int,
    ) -> float:
        base = 0.5
        if has_code:
            base += 0.2
        if has_content:
            base += 0.1
        if db_queries > 0:
            base += 0.05
        if sync_calls > 0:
            base += 0.05
        if signals >= 2:
            base += 0.05
        return min(base, 1.0)

    def _has_n_plus_one(self, code: str, full_content: str) -> bool:
        target = code or full_content
        if not target:
            return False
        loop_pattern = r"for\s+\w+\s+in\s+\w+\s*:"
        query_pattern = r"\.(?:get|filter|all|first|fetch|select)\s*\("
        return bool(re.search(loop_pattern, target)) and bool(
            re.search(query_pattern, target)
        )

    def _count_sync_external_calls(self, code: str) -> int:
        if not code:
            return 0
        patterns = [
            r"requests\.(?:get|post|put|delete)\(",
            r"urllib\.request\.urlopen\(",
            r"httpx\.(?:get|post|put|delete)\(",
        ]
        count = 0
        for p in patterns:
            count += len(re.findall(p, code))
        return count

    def _has_unbounded_query(self, code: str) -> bool:
        if not code:
            return False
        has_all = bool(re.search(r"\.all\s*\(\)", code))
        has_limit = bool(re.search(r"\.limit\s*\(", code)) or bool(
            re.search(r":limit\s*=>", code)
        )
        return has_all and not has_limit

    def _count_db_queries(self, code: str) -> int:
        if not code:
            return 0
        patterns = [
            r"\.(?:get|filter|all|first|fetch|select|query|execute)\s*\(",
            r"\.(?:save|create|update|delete|bulk_create)\s*\(",
            r"\.(?:filter|exclude|annotate|aggregate)\s*\(",
        ]
        count = 0
        for p in patterns:
            count += len(re.findall(p, code))
        return count

    def _has_sync_in_async(self, route: ParsedRoute, code: str) -> bool:
        if not code:
            return False
        is_async = bool(
            re.search(r"async\s+def\s+" + re.escape(route.handler_name), code)
        )
        sync_calls = self._count_sync_external_calls(code)
        return is_async and sync_calls > 0

    def _has_file_io(self, code: str) -> bool:
        if not code:
            return False
        patterns = [
            r"open\s*\(",
            r"\.read\s*\(",
            r"\.write\s*\(",
            r"Path\(",
            r"os\.path\.",
        ]
        return any(re.search(p, code) for p in patterns)

    def _has_high_cpu_complexity(self, code: str) -> bool:
        if not code:
            return False
        nested_loops = len(re.findall(r"for\s+\w+\s+in\s+\w+\s*:", code))
        heavy_ops = len(re.findall(r"(?:sorted|filter|map|reduce|comprehension)", code))
        return (nested_loops >= 2) or (nested_loops >= 1 and heavy_ops >= 2)

    def _has_memory_pressure(self, code: str) -> bool:
        if not code:
            return False
        large_alloc = bool(
            re.search(
                r"\[\s*\]\s*=\s*\[\s*\]|list\s*\(\s*range|\[\s*\w+\s+for\s+\w+\s+in\s+range",
                code,
            )
        )
        file_read = bool(re.search(r"\.read\s*\(\s*\)", code))
        return large_alloc or file_read

    def _memory_pressure_impact(self, code: str) -> int:
        impact = 0
        if re.search(r"\.read\s*\(\s*\)", code):
            impact += 100
        if re.search(r"list\s*\(\s*range", code):
            impact += 50
        if re.search(r"\[\s*\w+\s+for\s+\w+\s+in\s+range", code):
            impact += 50
        return impact

    def _count_serialization(self, code: str) -> int:
        if not code:
            return 0
        patterns = [
            r"json\.(?:dumps|loads)\(",
            r"pickle\.(?:dump|load|dumps|loads)\(",
            r"marshal\.(?:dump|load)\(",
            r"yaml\.(?:dump|load|safe_load)\(",
            r"xml\.(?:etree|dom|sax)",
            r"serialize|deserialize",
            r"\.serialize\(",
            r"\.to_json\(",
        ]
        count = 0
        for p in patterns:
            count += len(re.findall(p, code))
        return count

    def _has_no_caching(self, code: str) -> bool:
        if not code:
            return False
        has_cache = bool(
            re.search(
                r"\b(?:cache|memoize|lru_cache|redis|memcache)\b", code, re.IGNORECASE
            )
        )
        has_db_or_compute = bool(
            re.search(r"\.(?:get|filter|all|fetch|select|query)\s*\(", code)
            or re.search(r"(?:sorted|filter|map|reduce|comprehension)", code)
        )
        return has_db_or_compute and not has_cache

    def _loop_complexity(self, code: str) -> int:
        if not code:
            return 0
        loops = re.findall(r"for\s+\w+\s+in\s+\w+\s*:", code)
        nested = len(loops)
        if nested >= 3:
            return 5
        if nested >= 2:
            return 3
        if nested >= 1:
            return 1
        return 0

    def _estimate_p50_latency(
        self, db_queries: int, sync_calls: int, code: str, loop_score: int = 0
    ) -> int:
        base = LATENCY_BASE_MS
        unindexed = 0
        if code:
            unindexed = len(re.findall(r"\.(?:all|filter)\s*\(", code))
        db_latency = (db_queries - unindexed) * 5 + unindexed * 20
        sync_latency = sync_calls * 50
        loop_latency = loop_score * 15
        serialization = self._count_serialization(code) * 10
        memory = 20 if self._has_memory_pressure(code) else 0
        complexity = 30 if self._has_high_cpu_complexity(code) else 0
        return (
            base
            + db_latency
            + sync_latency
            + loop_latency
            + serialization
            + memory
            + complexity
        )

    def _calculate_breakpoint(self, rpm: int, p50_ms: int) -> int:
        response_time_sec = p50_ms / 1000
        if response_time_sec <= 0:
            return 10000
        breakpoint_val = int(rpm / max(response_time_sec, 0.001))
        return max(min(breakpoint_val, 100000), 1)
