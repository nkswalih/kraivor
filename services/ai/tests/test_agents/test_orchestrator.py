import pytest
from unittest.mock import AsyncMock, patch
from app.application.agents.orchestrator import OrchestratorNode
from app.application.agents.code_analyst import CodeAnalystNode
from app.application.agents.explainer import ExplainerNode
from app.application.agents.graph import build_agent_graph


pytestmark = pytest.mark.unit


class TestOrchestrator:
    async def test_simple_qa_shortcut(self):
        node = OrchestratorNode()
        with patch.object(node, "key_resolver") as resolver:
            resolver.resolve = AsyncMock(return_value=("test-key", "google"))
            with patch("app.application.agents.orchestrator.LLMClient") as mock_client:
                instance = mock_client.return_value
                instance.generate = AsyncMock(return_value={
                    "content": '{"intent": "simple_qa", "complexity": "simple", "required_agents": []}',
                    "provider": "google", "model": "gemini-flash-1.5",
                    "input_tokens": 10, "output_tokens": 20, "cost": 0.0, "latency_ms": 50,
                })
                result = await node({"user_id": "u1", "message": "what is python?", "stream": False})

        assert result["intent"] == "simple_qa"
        assert result["required_agents"] == []


class TestGraph:
    async def test_build_agent_graph(self):
        graph = build_agent_graph()
        assert graph is not None
        assert graph.get_graph() is not None
