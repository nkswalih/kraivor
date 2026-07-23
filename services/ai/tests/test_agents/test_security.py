import pytest
from unittest.mock import AsyncMock, patch

from app.application.agents.explainer import ExplainerNode
from app.application.agents.security import SecurityAnalystNode

pytestmark = pytest.mark.unit


class TestSecurityAnalyst:
    async def test_security_analysis(self):
        node = SecurityAnalystNode()
        with patch.object(node, "failover") as mock_failover:
            mock_failover.execute = AsyncMock(
                return_value={
                    "content": "No critical vulnerabilities found.",
                    "input_tokens": 5,
                    "output_tokens": 10,
                    "cost": 0.0,
                    "latency_ms": 50,
                }
            )
            result = await node(
                {
                    "user_id": "u1",
                    "code_findings": ["test"],
                    "assembled_context": "test code",
                }
            )
        assert result["security_findings"] is not None


class TestExplainer:
    async def test_explainer_synthesizes_findings(self):
        node = ExplainerNode()
        with patch.object(node, "failover") as mock_failover:
            mock_failover.execute = AsyncMock(
                return_value={
                    "content": "## Summary\nGood code.",
                    "input_tokens": 5,
                    "output_tokens": 10,
                    "cost": 0.0,
                    "latency_ms": 50,
                }
            )
            result = await node(
                {
                    "user_id": "u1",
                    "code_findings": ["Bug found"],
                    "assembled_context": "code context",
                    "message": "review this",
                }
            )
        assert result["response"] is not None
        assert "Summary" in result["response"]
