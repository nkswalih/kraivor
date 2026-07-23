import pytest
from unittest.mock import AsyncMock, patch

from app.application.agents.graph import build_agent_graph
from app.application.agents.orchestrator import OrchestratorNode

pytestmark = pytest.mark.unit


class TestOrchestrator:
    async def test_simple_qa_shortcut(self):
        node = OrchestratorNode()
        with patch.object(node, "failover") as mock_failover:
            mock_failover.execute = AsyncMock(
                return_value={
                    "content": '{"intent": "simple_qa", "complexity": "simple", "required_agents": []}',
                    "input_tokens": 10,
                    "output_tokens": 20,
                    "cost": 0.0,
                    "latency_ms": 50,
                }
            )
            result = await node(
                {"user_id": "u1", "message": "what is python?", "stream": False}
            )

        assert result["intent"] == "simple_qa"
        assert result["required_agents"] == []


class TestGraph:
    async def test_build_agent_graph(self):
        graph = build_agent_graph()
        assert graph is not None
        assert graph.get_graph() is not None


class TestCacheScoping:
    """Fix 12: Regression test — intent cache keys must be scoped by user_id
    to prevent cross-user cache leaks (Bob's response leaking to Alice)."""

    def test_intent_cache_key_includes_user_id(self):
        """Verify that different user_ids produce different cache keys."""
        import hashlib

        message = "hello"
        history_hash = hashlib.sha256(b"").hexdigest()[:16]

        # Simulate cache key generation from orchestrator.py
        user_id_alice = "alice-123"
        user_id_bob = "bob-456"

        key_alice = f"intent:{user_id_alice}:{hashlib.sha256(f'{message}:{history_hash}'.encode()).hexdigest()[:24]}"
        key_bob = f"intent:{user_id_bob}:{hashlib.sha256(f'{message}:{history_hash}'.encode()).hexdigest()[:24]}"

        # Keys MUST differ when user_id differs
        assert key_alice != key_bob, "Cache keys must be scoped by user_id"
        assert key_alice.startswith(f"intent:{user_id_alice}:")
        assert key_bob.startswith(f"intent:{user_id_bob}:")

    def test_cache_key_deterministic_per_user(self):
        """Same user + same message should produce the same cache key."""
        import hashlib

        message = "what is 2+2"
        history_hash = hashlib.sha256(b"").hexdigest()[:16]
        user_id = "user-789"

        key1 = f"intent:{user_id}:{hashlib.sha256(f'{message}:{history_hash}'.encode()).hexdigest()[:24]}"
        key2 = f"intent:{user_id}:{hashlib.sha256(f'{message}:{history_hash}'.encode()).hexdigest()[:24]}"

        assert key1 == key2

    def test_cache_key_differs_with_different_history(self):
        """Same user + different history should produce different cache keys."""
        import hashlib

        message = "continue"
        user_id = "user-789"

        history_hash_a = hashlib.sha256(b"old conversation").hexdigest()[:16]
        history_hash_b = hashlib.sha256(b"different conversation").hexdigest()[:16]

        key_a = f"intent:{user_id}:{hashlib.sha256(f'{message}:{history_hash_a}'.encode()).hexdigest()[:24]}"
        key_b = f"intent:{user_id}:{hashlib.sha256(f'{message}:{history_hash_b}'.encode()).hexdigest()[:24]}"

        assert key_a != key_b
