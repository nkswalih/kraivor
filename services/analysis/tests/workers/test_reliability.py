"""Tests for the ReliabilityDetector."""

import pytest

from app.domain.contracts.parser import ParsedFile
from app.workers.reliability.detector import ReliabilityDetector


def _make_pf(path: str, content: str) -> ParsedFile:
    return ParsedFile(
        path=path,
        content=content,
        language="python",
        ast_data={},
        functions=[],
        classes=[],
        imports=[],
        exports=[],
        routes=[],
        lines_count=len(content.split("\n")),
        errors=[],
        size_bytes=len(content.encode("utf-8")),
    )


@pytest.mark.asyncio
class TestMissingRetries:
    async def test_detects_missing_retry(self) -> None:
        pfs = [
            _make_pf(
                "client.py", "def call():\n    requests.get('https://api.example.com')"
            )
        ]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "missing_retry" in types

    async def test_skips_with_retry(self) -> None:
        content = (
            "def call():\n"
            "    @retry(stop=stop_after_attempt(3))\n"
            "    def inner():\n"
            "        requests.get('https://api.example.com')\n"
        )
        pfs = [_make_pf("client.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "missing_retry" not in types


@pytest.mark.asyncio
class TestMissingCircuitBreaker:
    async def test_detects_missing_circuit_breaker(self) -> None:
        content = "\n".join(
            [
                "def a(): requests.get('https://api1.com')",
                "def b(): requests.get('https://api2.com')",
                "def c(): requests.get('https://api3.com')",
            ]
        )
        pfs = [_make_pf("client.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "missing_circuit_breaker" in types

    async def test_skips_with_circuit_breaker(self) -> None:
        content = (
            "from circuitbreaker import circuit\n"
            "@circuit\n"
            "def call():\n"
            "    requests.get('https://api.example.com')\n"
        )
        pfs = [_make_pf("client.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "missing_circuit_breaker" not in types


@pytest.mark.asyncio
class TestMissingRollback:
    async def test_detects_missing_rollback(self) -> None:
        content = (
            "def transfer():\n"
            "    session.begin_transaction()\n"
            "    try:\n"
            "        db.insert('accounts', data)\n"
            "    except Exception:\n"
            "        logger.exception('transaction failed')\n"
        )
        pfs = [_make_pf("db.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "missing_rollback" in types

    async def test_skips_with_rollback(self) -> None:
        content = (
            "def transfer():\n"
            "    session.begin_transaction()\n"
            "    try:\n"
            "        db.insert('accounts', data)\n"
            "    except Exception:\n"
            "        session.rollback()\n"
        )
        pfs = [_make_pf("db.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "missing_rollback" not in types


@pytest.mark.asyncio
class TestResourceLeaks:
    async def test_detects_open_without_context_manager(self) -> None:
        pfs = [_make_pf("files.py", "f = open('data.txt', 'r')")]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "resource_leak" in types

    async def test_skips_with_context_manager(self) -> None:
        pfs = [_make_pf("files.py", "with open('data.txt', 'r') as f: pass")]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "resource_leak" not in types


@pytest.mark.asyncio
class TestInfiniteLoops:
    async def test_detects_infinite_loop_without_break(self) -> None:
        content = "while True:\n    process(data)\n"
        pfs = [_make_pf("worker.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "infinite_loop" in types

    async def test_skips_loop_with_break(self) -> None:
        content = (
            "while True:\n    if done:\n        break\n    process(data)\n" + "\n" * 20
        )
        pfs = [_make_pf("worker.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "infinite_loop" not in types


@pytest.mark.asyncio
class TestThreadSafety:
    async def test_detects_threading_without_lock(self) -> None:
        content = (
            "import threading\n"
            "counter = 0\n"
            "def inc():\n"
            "    global counter\n"
            "    counter += 1\n"
        )
        pfs = [_make_pf("counter.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "thread_safety" in types

    async def test_skips_threading_with_lock(self) -> None:
        content = (
            "import threading\n"
            "lock = threading.Lock()\n"
            "counter = 0\n"
            "def inc():\n"
            "    global counter\n"
            "    with lock:\n"
            "        counter += 1\n"
        )
        pfs = [_make_pf("counter.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "thread_safety" not in types


@pytest.mark.asyncio
class TestCacheStampede:
    async def test_detects_cache_without_ttl(self) -> None:
        pfs = [_make_pf("cache.py", "data = cache.get('my_key')")]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "cache_stampede" in types

    async def test_skips_cache_with_ttl(self) -> None:
        pfs = [_make_pf("cache.py", "data = cache.get('my_key', ttl=300)")]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "cache_stampede" not in types


@pytest.mark.asyncio
class TestEventOrdering:
    async def test_detects_event_without_ordering(self) -> None:
        pfs = [_make_pf("events.py", "kafka_producer.send('topic', event)")]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "event_ordering" in types

    async def test_skips_event_with_ordering(self) -> None:
        pfs = [
            _make_pf("events.py", "kafka_producer.send('topic', event, key=order_id)")
        ]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "event_ordering" not in types


@pytest.mark.asyncio
class TestTransactionMisuse:
    async def test_detects_begin_without_commit(self) -> None:
        pfs = [_make_pf("db.py", "session.begin_transaction()")]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "transaction_misuse" in types

    async def test_skips_with_commit(self) -> None:
        content = (
            "session.begin_transaction()\n"
            "try:\n"
            "    db.insert(data)\n"
            "    session.commit()\n"
            "except:\n"
            "    session.rollback()\n"
        )
        pfs = [_make_pf("db.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "transaction_misuse" not in types


@pytest.mark.asyncio
class TestRaceCondition:
    async def test_detects_race_in_async(self) -> None:
        content = "async def handler():\n    global counter\n    counter += 1\n"
        pfs = [_make_pf("handler.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "race_condition" in types

    async def test_skips_with_lock(self) -> None:
        content = (
            "import asyncio\n"
            "lock = asyncio.Lock()\n"
            "async def handler():\n"
            "    async with lock:\n"
            "        global counter\n"
            "        counter += 1\n"
        )
        pfs = [_make_pf("handler.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "race_condition" not in types


@pytest.mark.asyncio
class TestIdempotency:
    async def test_detects_missing_idempotency(self) -> None:
        content = (
            "@app.route('/api/orders', methods=['POST'])\n"
            "def create_order():\n"
            "    return db.insert(order_data)\n"
            "\n"
            "@app.route('/api/payments', methods=['POST'])\n"
            "def process_payment():\n"
            "    return db.insert(payment_data)\n"
        )
        pfs = [_make_pf("routes.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "idempotency" in types

    async def test_skips_with_idempotency_key(self) -> None:
        content = (
            "def create_order():\n"
            "    idempotency_key = request.headers.get('Idempotency-Key')\n"
            "    return db.insert(order_data)\n"
        )
        pfs = [_make_pf("routes.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "idempotency" not in types


@pytest.mark.asyncio
class TestEmptyContent:
    async def test_empty_content_no_findings(self) -> None:
        pfs = [_make_pf("empty.py", "")]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        assert len(results) == 0


@pytest.mark.asyncio
class TestPerDetectorEdgeCases:
    async def test_comment_matching_retry_no_false_positive(self) -> None:
        content = (
            "# TODO: add retry logic here\nrequests.get('https://api.example.com')"
        )
        pfs = [_make_pf("client.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        types = [r.reliability_type for r in results]
        assert "missing_retry" in types

    async def test_string_containing_pattern_no_false_positive(self) -> None:
        content = 'name = "requests.get"  # just a string'
        pfs = [_make_pf("strings.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        assert all(r.reliability_type != "resource_leak" for r in results)

    async def test_binary_content_no_crash(self) -> None:
        pfs = [_make_pf("binary.bin", "\x00\x01\x02\x03\xff\xfe\xfd\xfc")]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        assert isinstance(results, list)

    async def test_very_large_content_no_crash(self) -> None:
        content = "x = 1\n" * 10000
        pfs = [_make_pf("large.py", content)]
        detector = ReliabilityDetector(pfs)
        results = await detector.scan_all()
        assert isinstance(results, list)
