import re

from app.core.logging import get_logger
from app.domain.contracts.parser import ParsedFile
from app.workers.reliability.models import ReliabilityFinding

logger = get_logger(__name__)


class ReliabilityDetector:
    """Detects reliability anti-patterns in source code.

    Covers:
      - Missing retries on external calls
      - Missing circuit breakers
      - Missing rollback in transactions
      - Transaction misuse
      - Race conditions
      - Resource leaks (files, connections)
      - Infinite loops / recursion
      - Thread safety issues
      - Cache stampede risks
      - Idempotency problems
      - Event ordering risks
    """

    def __init__(self, parsed_files: list[ParsedFile]) -> None:
        self.parsed_files = parsed_files

    async def scan_all(self) -> list[ReliabilityFinding]:
        results: list[ReliabilityFinding] = []
        for pf in self.parsed_files:
            content = pf.content
            file_path = pf.path
            results.extend(self._detect_missing_retries(file_path, content))
            results.extend(self._detect_missing_circuit_breaker(file_path, content))
            results.extend(self._detect_missing_rollback(file_path, content))
            results.extend(self._detect_transaction_misuse(file_path, content))
            results.extend(self._detect_race_condition(file_path, content))
            results.extend(self._detect_resource_leaks(file_path, content))
            results.extend(self._detect_infinite_loops(file_path, content))
            results.extend(self._detect_thread_safety(file_path, content))
            results.extend(self._detect_cache_stampede(file_path, content))
            results.extend(self._detect_idempotency(file_path, content))
            results.extend(self._detect_event_ordering(file_path, content))
            results.extend(self._detect_missing_timeouts(file_path, content))
            results.extend(self._detect_error_swallowing(file_path, content))
            results.extend(self._detect_unawaited_tasks(file_path, content))
            results.extend(self._detect_connection_pool_misuse(file_path, content))
            results.extend(self._detect_missing_fallback(file_path, content))
            results.extend(self._detect_stale_cache(file_path, content))
            results.extend(self._detect_dead_letter(file_path, content))
        return results

    def _detect_missing_retries(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect external calls without retry logic."""
        findings: list[ReliabilityFinding] = []
        external_call_patterns = [
            r'(?i)requests?\.(?:get|post|put|delete|patch|request)\s*\(',
            r'(?i)httpx\.(?:get|post|put|delete|patch|request|AsyncClient)\s*\(',
            r'(?i)aiohttp\.ClientSession\(\)',
            r'(?i)urllib\.request\.urlopen\(',
            r'(?i)(?:HttpClient|WebClient|RestClient)\.(?:SendAsync|GetAsync|PostAsync|PutAsync|DeleteAsync)\s*\(',
        ]
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pattern_str in external_call_patterns:
                if re.search(pattern_str, line):
                    nearby_lines = lines[max(0, line_num - 6):min(len(lines), line_num + 2)]
                    nearby_text = "\n".join(nearby_lines).lower()
                    has_retry_nearby = any(
                        kw in nearby_text
                        for kw in ("retry(", "retry_", "backoff(", "max_retries", "retry_count", "retry_attempt", "retry.stop")
                    )
                    if not has_retry_nearby:
                        findings.append(ReliabilityFinding(
                            reliability_type="missing_retry",
                            severity="medium",
                            title="External call without retry logic",
                            description="This external service call has no retry mechanism. Transient failures will propagate.",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Add retry with exponential backoff: tenacity, backoff, or Polly library",
                            confidence=0.7,
                        ))
                    break
        return findings

    def _detect_missing_circuit_breaker(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect external calls in HA contexts without circuit breaker."""
        findings: list[ReliabilityFinding] = []
        has_circuit_breaker = any(
            kw in content.lower()
            for kw in ("circuit_breaker", "circuitbreaker", "CircuitBreaker", "breaker")
        )
        if has_circuit_breaker:
            return findings

        external_calls = [
            r'(?i)requests?\.(?:get|post|put|delete|patch)\s*\(',
            r'(?i)httpx\.(?:get|post|put|delete|patch)\s*\(',
            r'(?i)(?:HttpClient|WebClient)\.(?:SendAsync|GetAsync|PostAsync)\s*\(',
        ]
        lines = content.split("\n")
        count = 0
        first_line: int | None = None
        snippet = ""
        for line_num, line in enumerate(lines, 1):
            for pat in external_calls:
                if re.search(pat, line):
                    count += 1
                    if first_line is None:
                        first_line = line_num
                        snippet = line.strip()
                    break
        if count >= 3:
            findings.append(ReliabilityFinding(
                reliability_type="missing_circuit_breaker",
                severity="medium",
                title="Multiple external calls without circuit breaker",
                description=f"File has {count}+ external HTTP calls but no circuit breaker pattern",
                file_path=file_path,
                line_start=first_line,
                code_snippet=snippet,
                recommendation="Add circuit breaker: pybreaker, resilience4j, or Hystrix for downstream calls",
                confidence=0.6,
            ))
        return findings

    def _detect_missing_rollback(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect database writes in try/except without rollback."""
        findings: list[ReliabilityFinding] = []
        lines = content.split("\n")
        try_blocks: list[tuple[int, int]] = []
        depth = 0
        try_start = -1
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("try:"):
                depth = 1
                try_start = line_num
            elif try_start > -1:
                if stripped.startswith("except") or stripped.startswith("finally"):
                    try_blocks.append((try_start, line_num))
                    try_start = -1

        has_transaction_in_file = any(
            kw in content.lower()
            for kw in ("transaction", "begin_transaction", "session.begin", "unit_of_work", "uow")
        )
        for try_start, except_line in try_blocks:
            block_text = "\n".join(lines[max(0, try_start - 2):except_line + 3])
            has_db_write = any(
                kw in block_text.lower()
                for kw in ("insert", "update", "delete", "save", "create", "put", "post")
            )
            has_rollback = bool(
                re.search(r'(?i)(?:rollback|roll_back|undo)\s*\(', block_text)
                or re.search(r'(?i)\brollback\b', block_text)
            )
            if has_db_write and not has_rollback and has_transaction_in_file:
                findings.append(ReliabilityFinding(
                    reliability_type="missing_rollback",
                    severity="high",
                    title="Database write without rollback in exception handler",
                    description="Transaction has database writes but no rollback on exception — data could be corrupted",
                    file_path=file_path,
                    line_start=try_start,
                    line_end=except_line,
                    code_snippet=block_text[:300],
                    recommendation="Add rollback in the except block: session.rollback() or uow.rollback()",
                    confidence=0.75,
                ))
        return findings

    def _detect_transaction_misuse(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect non-atomic operations and missing commit/rollback."""
        findings: list[ReliabilityFinding] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(?i)(?:begin|start)_(?:transaction|session)', line):
                surrounding = "\n".join(lines[max(0, line_num - 2):min(len(lines), line_num + 15)])
                has_commit = "commit" in surrounding.lower()
                has_except = "except" in surrounding.lower()
                if not has_commit and not has_except:
                    findings.append(ReliabilityFinding(
                        reliability_type="transaction_misuse",
                        severity="high",
                        title="Transaction started but may not complete",
                        description="Transaction/session begin without commit or rollback visible in nearby scope",
                        file_path=file_path,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Ensure every begin_transaction has a corresponding commit or rollback",
                        confidence=0.6,
                    ))
        return findings

    def _detect_race_condition(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect shared mutable state without locks in async contexts."""
        findings: list[ReliabilityFinding] = []
        if not re.search(r'(?i)(?:async|await|asyncio|@app\.route)', content):
            return findings

        has_lock = any(
            kw in content.lower()
            for kw in ("lock", "mutex", "semaphore", "threading.lock", "asyncio.lock", "synchronized")
        )
        shared_state_patterns = [
            r'(?i)(?:global|nonlocal)\s+\w+',
            r'(?i)(?:class|self)\.\w+\s*[+]=',
            r'(?i)(?:class|self)\.\w+\s*=\s*(?:self\.\w+\s*[+\-*/])',
        ]
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pat in shared_state_patterns:
                if re.search(pat, line) and not has_lock:
                    findings.append(ReliabilityFinding(
                        reliability_type="race_condition",
                        severity="high",
                        title="Potential race condition on shared state",
                        description="Shared mutable state modified in async context without synchronization",
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip(),
                        recommendation="Use asyncio.Lock or threading.Lock to protect shared state mutations",
                        confidence=0.55,
                    ))
                    break
        return findings

    def _detect_resource_leaks(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect file/connection opens without context managers."""
        findings: list[ReliabilityFinding] = []
        patterns = [
            (r'(?i)open\s*\([^)]*\)(?!\s*as\s)', "File handle may not be closed — use 'with open() as f:'"),
            (r'(?i)(?:create_connection|connect)\s*\([^)]*\)(?!\s*as\s)', "Connection may not be closed — use context manager"),
            (r'(?i)(?:StringIO|BytesIO)\s*\([^)]*\)(?!\s*as\s)', "I/O stream may not be closed — use context manager"),
        ]
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pat, msg in patterns:
                if re.search(pat, line):
                    if "with" not in line.lower():
                        findings.append(ReliabilityFinding(
                            reliability_type="resource_leak",
                            severity="medium",
                            title="Potential resource leak",
                            description=msg,
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip(),
                            recommendation="Use a context manager ('with' statement) to ensure proper cleanup",
                            confidence=0.7,
                        ))
                    break
        return findings

    def _detect_infinite_loops(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect while True loops without break conditions."""
        findings: list[ReliabilityFinding] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(?i)while\s+True\s*:', line):
                surrounding = "\n".join(lines[line_num:min(len(lines), line_num + 20)])
                has_break = "break" in surrounding or "return" in surrounding
                if not has_break:
                    findings.append(ReliabilityFinding(
                        reliability_type="infinite_loop",
                        severity="medium",
                        title="Infinite loop without break condition",
                        description="'while True' loop without break/return in the first 20 lines",
                        file_path=file_path,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Add break or return condition, or use a bounded loop with max iterations",
                        confidence=0.6,
                    ))
        return findings

    def _detect_thread_safety(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect threading without proper synchronization."""
        findings: list[ReliabilityFinding] = []
        has_threading = any(
            kw in content.lower()
            for kw in ("threading", "threadpool", "concurrent.futures", "multiprocessing")
        )
        if not has_threading:
            return findings

        has_sync = any(
            kw in content.lower()
            for kw in ("lock", "mutex", "semaphore", "threading.lock", "threading.rlock", "synchronized")
        )
        if not has_sync:
            lines = content.split("\n")
            for line_num, line in enumerate(lines, 1):
                if re.search(r'(?i)(?:threading|ThreadPoolExecutor|multiprocessing)', line):
                    findings.append(ReliabilityFinding(
                        reliability_type="thread_safety",
                        severity="high",
                        title="Threading without synchronization",
                        description="Thread/thread pool usage detected but no lock or synchronization mechanism found",
                        file_path=file_path,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Add threading.Lock or use thread-safe data structures",
                        confidence=0.65,
                    ))
                    break
        return findings

    def _detect_cache_stampede(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect cache reads without TTL synchronization."""
        findings: list[ReliabilityFinding] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(?i)(?:cache|redis|memcached)\.(?:get|fetch|retrieve)\s*\(', line):
                surrounding = "\n".join(lines[max(0, line_num - 3):min(len(lines), line_num + 5)])
                has_ttl = any(
                    kw in surrounding.lower()
                    for kw in ("ttl", "expire", "timeout", "lock", "mutex")
                )
                if not has_ttl:
                    findings.append(ReliabilityFinding(
                        reliability_type="cache_stampede",
                        severity="low",
                        title="Cache read without stampede protection",
                        description="Cache read without TTL or lock — concurrent requests may all recompute simultaneously",
                        file_path=file_path,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Use TTL with jitter or a mutex around cache recomputation",
                        confidence=0.5,
                    ))
        return findings

    def _detect_idempotency(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect state-changing operations without idempotency keys."""
        findings: list[ReliabilityFinding] = []
        has_idempotency = any(
            kw in content.lower()
            for kw in ("idempot", "idempotency_key", "idempotent", "request_id", "dedup")
        )
        if has_idempotency:
            return findings

        routes: list[dict[str, object]] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(?i)(?:@route|@app\.|@router\.|def\s+\w+.*request)', line):
                routes.append({"line": line_num, "text": line.strip()})

        mutating_count = 0
        first_mutating: int | None = None
        snippet = ""
        for r in routes:
            if not re.search(r'(?i)(?:GET|get|list|fetch|read|query)', r["text"]):
                mutating_count += 1
                if first_mutating is None:
                    first_mutating = r["line"]
                    snippet = r["text"]

        if mutating_count >= 2:
            findings.append(ReliabilityFinding(
                reliability_type="idempotency",
                severity="low",
                title="State-changing operations lack idempotency keys",
                description=f"{mutating_count}+ mutating operations without idempotency keys — retries may cause duplicates",
                file_path=file_path,
                line_start=first_mutating,
                code_snippet=snippet,
                recommendation="Add idempotency keys to all mutating API endpoints (POST, PUT, PATCH, DELETE)",
                confidence=0.5,
            ))
        return findings

    def _detect_event_ordering(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect event/message processing without ordering guarantees."""
        findings: list[ReliabilityFinding] = []
        has_messaging = any(
            kw in content.lower()
            for kw in ("kafka", "rabbitmq", "publish", "subscribe", "event", "message_queue", "sqs", "pubsub")
        )
        if not has_messaging:
            return findings

        has_ordering = any(
            kw in content.lower()
            for kw in ("sequence", "ordering", "order_key", "partition", "sequence_number", "version", "key=", "order_id")
        )
        if not has_ordering:
            lines = content.split("\n")
            for line_num, line in enumerate(lines, 1):
                if re.search(r'(?i)(?:publish|send|produce|emit)\(', line):
                    findings.append(ReliabilityFinding(
                        reliability_type="event_ordering",
                        severity="medium",
                        title="Event processing without ordering guarantees",
                        description="Event/message publishing detected without ordering or sequence tracking",
                        file_path=file_path,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Add sequence numbers, version fields, or use ordered partitions for critical events",
                        confidence=0.55,
                    ))
                    break
        return findings

    def _detect_missing_timeouts(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect external calls without timeout configuration."""
        findings: list[ReliabilityFinding] = []
        patterns = [
            r'(?i)requests?\.(?:get|post|put|delete|patch|request)\s*\(',
            r'(?i)httpx\.(?:get|post|put|delete|patch)\s*\(',
            r'(?i)aiohttp\.ClientSession\(\)',
            r'(?i)urllib\.request\.urlopen\(',
        ]
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            for pat in patterns:
                if re.search(pat, line):
                    has_timeout = any(
                        kw in line.lower()
                        for kw in ("timeout", "timeout=", "settimeout", ".timeout(")
                    )
                    if not has_timeout:
                        findings.append(ReliabilityFinding(
                            reliability_type="missing_timeout",
                            severity="medium",
                            title="External call without timeout",
                            description="HTTP/network call without timeout — can hang indefinitely under load",
                            file_path=file_path,
                            line_start=line_num,
                            code_snippet=line.strip(),
                            recommendation="Add a timeout argument to the call (e.g., timeout=30)",
                            confidence=0.65,
                        ))
                    break
        return findings

    def _detect_error_swallowing(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect bare except: blocks that silence all exceptions."""
        findings: list[ReliabilityFinding] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r'^except\s*:', stripped) or re.match(r'^except\s*$', stripped):
                next_lines = "\n".join(lines[line_num:min(len(lines), line_num + 3)])
                has_raise = "raise" in next_lines or "pass" not in next_lines[:60]
                if not has_raise:
                    findings.append(ReliabilityFinding(
                        reliability_type="error_swallowing",
                        severity="high",
                        title="Bare except silently swallows all exceptions",
                        description="'except:' block without exception type catches everything, making debugging difficult",
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip(),
                        recommendation="Catch specific exception types. Avoid bare except: — log and re-raise when appropriate.",
                        confidence=0.8,
                    ))
        return findings

    def _detect_unawaited_tasks(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect async calls without await keyword."""
        findings: list[ReliabilityFinding] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(?i)create_task|ensure_future|Task\(\)', line):
                finding = ReliabilityFinding(
                    reliability_type="unawaited_task",
                    severity="medium",
                    title="Async task created without await",
                    description="Async task or future created but may not be awaited — errors will be silently lost",
                    file_path=file_path,
                    line_start=line_num,
                    code_snippet=line.strip(),
                    recommendation="Use await or asyncio.gather() to ensure task completion and error propagation",
                    confidence=0.5,
                )
                findings.append(finding)
        return findings

    def _detect_connection_pool_misuse(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect connection creation inside request handlers (no pooling)."""
        findings: list[ReliabilityFinding] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(?i)def\s+\w+\(.*request.*\):', line) or re.search(r'(?i)@app\.route|@router\.', line):
                surrounding = "\n".join(lines[line_num:min(len(lines), line_num + 15)])
                has_pool = any(
                    kw in surrounding.lower()
                    for kw in ("connection_pool", "pool", "session_pool", "engine", "client_pool")
                )
                has_new_connection = bool(
                    re.search(r'(?i)(?:create_connection|new\s+connection|connect\s*\(|psycopg2\.connect|sqlite3\.connect)', surrounding)
                )
                if has_new_connection and not has_pool:
                    findings.append(ReliabilityFinding(
                        reliability_type="connection_pool_misuse",
                        severity="medium",
                        title="Connection created inside request handler",
                        description="New database/network connection created per request instead of using a connection pool",
                        file_path=file_path,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Use a connection pool (SQLAlchemy engine, Redis ConnectionPool, etc.)",
                        confidence=0.55,
                    ))
                    break
        return findings

    def _detect_missing_fallback(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect external calls without fallback/default on failure."""
        findings: list[ReliabilityFinding] = []
        lines = content.split("\n")
        in_handler = False
        handler_line = 0
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(?i)def\s+\w+\(', line):
                in_handler = True
                handler_line = line_num
            if in_handler and line.strip() and not line.startswith(" "):
                in_handler = False
            if not in_handler:
                continue
            if re.search(r'(?i)(?:requests?|httpx|aiohttp)\.(?:get|post)\s*\(', line):
                surrounding = "\n".join(lines[max(0, line_num - 1):min(len(lines), line_num + 5)])
                has_fallback = any(
                    kw in surrounding.lower()
                    for kw in ("except", "fallback", "default", "or ", "else:", "try:")
                )
                if not has_fallback:
                    findings.append(ReliabilityFinding(
                        reliability_type="missing_fallback",
                        severity="low",
                        title="External call without fallback",
                        description="External service call without fallback or default — failure will propagate to users",
                        file_path=file_path,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Add try/except with fallback: cached response, default value, or degraded mode",
                        confidence=0.5,
                    ))
        return findings

    def _detect_stale_cache(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect cache writes without TTL/expiry."""
        findings: list[ReliabilityFinding] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(?i)(?:cache|redis|memcached)\.(?:set|put|store|add)\s*\(', line):
                has_ttl = "ttl" in line.lower() or "expire" in line.lower() or "timeout" in line.lower()
                if not has_ttl:
                    findings.append(ReliabilityFinding(
                        reliability_type="stale_cache",
                        severity="low",
                        title="Cache write without TTL/expiry",
                        description="Data stored in cache without TTL — stale data will never be refreshed",
                        file_path=file_path,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Set TTL/expiry on all cache writes to prevent stale data accumulation",
                        confidence=0.6,
                    ))
        return findings

    def _detect_dead_letter(self, file_path: str, content: str) -> list[ReliabilityFinding]:
        """Detect message consumers without dead-letter or error handling."""
        findings: list[ReliabilityFinding] = []
        lines = content.split("\n")
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(?i)(?:def\s+\w+.*event|def\s+\w+.*message|def\s+\w+.*handle_\w+)', line):
                surrounding = "\n".join(lines[line_num:min(len(lines), line_num + 10)])
                has_dead_letter = any(
                    kw in surrounding.lower()
                    for kw in ("dead_letter", "dlq", "dead-letter", "reject", "nack", "retry_attempt", "max_retries")
                )
                has_messaging = any(
                    kw in content.lower()
                    for kw in ("kafka", "rabbitmq", "sqs", "pubsub", "message_queue", "event_bus")
                )
                if has_messaging and not has_dead_letter:
                    findings.append(ReliabilityFinding(
                        reliability_type="dead_letter",
                        severity="medium",
                        title="Message handler without dead-letter handling",
                        description="Event/message consumer without dead-letter queue or retry limit — poison messages loop forever",
                        file_path=file_path,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Add dead-letter queue, max retries, or nack/reject for unprocessable messages",
                        confidence=0.55,
                    ))
                    break
        return findings
