"""LangGraph agent pipeline for the AI service.

Orchestrator → [tools | explainer | agents] → end

Agent chain:
  context_assembler → [analysts] → evidence_gatherer → explainer → end

When ``enable_parallel_analysts`` is True and the orchestrator routes to
``context_assembler``, the four specialist nodes (code_analyst, security,
architecture, performance) run concurrently via ``asyncio.gather``.
"""

import asyncio
import logging

from langgraph.graph import END, StateGraph

from app.application.agents.architecture import ArchitectureAnalystNode
from app.application.agents.code_analyst import CodeAnalystNode
from app.application.agents.context_assembler import ContextAssemblerNode
from app.application.agents.evidence_gatherer import EvidenceGathererNode
from app.application.agents.explainer import ExplainerNode
from app.application.agents.orchestrator import OrchestratorNode
from app.application.agents.performance import PerformanceAnalystNode
from app.application.agents.security import SecurityAnalystNode
from app.application.agents.state import AgentState
from app.application.agents.tool_executor import ToolExecutorNode
from app.application.tools.workspace_tools import WorkspaceTools
from app.core.config import settings

logger = logging.getLogger(__name__)


class _ParallelAnalystNode:
    """Runs the four specialist analysts concurrently via asyncio.gather.

    Each analyst is independent — they read from assembled_context and
    write to their own state keys.  This node replaces the sequential
    chain when ``settings.enable_parallel_analysts`` is True.
    """

    def __init__(self):
        self._analysts = {
            "code_analyst": CodeAnalystNode(),
            "security_analyst": SecurityAnalystNode(),
            "architecture_analyst": ArchitectureAnalystNode(),
            "performance_analyst": PerformanceAnalystNode(),
        }

    async def __call__(self, state: dict) -> dict:
        async def _run(name: str, node):
            try:
                return name, await node(state)
            except Exception as exc:
                logger.error("parallel_analyst=%s failed: %s", name, exc)
                return name, {}

        results = await asyncio.gather(
            *[_run(n, nd) for n, nd in self._analysts.items()]
        )
        merged = {}
        for name, result in results:
            if isinstance(result, dict):
                merged.update(result)
        return merged


def build_agent_graph(client=None) -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("orchestrator", OrchestratorNode())

    if client is not None:
        workspace_tools = WorkspaceTools(client)
        builder.add_node("tool_executor", ToolExecutorNode(workspace_tools))
    else:
        class _NoopToolExecutor:
            async def __call__(self, state: dict) -> dict:
                return {"tool_results": None, "tool_calls": [], "response": None}

        builder.add_node("tool_executor", _NoopToolExecutor())

    builder.add_node("evidence_gatherer", EvidenceGathererNode())
    builder.add_node("context_assembler", ContextAssemblerNode())

    if settings.enable_parallel_analysts:
        builder.add_node("code_analyst", _ParallelAnalystNode())
    else:
        builder.add_node("code_analyst", CodeAnalystNode())
        builder.add_node("security_analyst", SecurityAnalystNode())
        builder.add_node("architecture_analyst", ArchitectureAnalystNode())
        builder.add_node("performance_analyst", PerformanceAnalystNode())

    builder.add_node("explainer", ExplainerNode())

    builder.set_entry_point("orchestrator")

    # ── Routing functions ──────────────────────────────────────

    def route_after_orchestrator(state: AgentState) -> str:
        if state.get("response"):
            return "end"

        needs_tools = state.get("needs_tools", False)
        needs_rag = state.get("needs_rag", False)
        needs_evidence = state.get("needs_evidence", False)
        required = state.get("required_agents", [])

        if needs_tools:
            return "tool_executor"
        if needs_evidence:
            return "evidence_gatherer"
        if needs_rag or required:
            return "context_assembler"
        return "end"

    def route_after_tools(state: AgentState) -> str:
        if state.get("response"):
            return "end"

        needs_rag = state.get("needs_rag", False)
        required = state.get("required_agents", [])

        if needs_rag or required:
            return "context_assembler"
        return "end"

    def route_after_evidence(state: AgentState) -> str:
        needs_rag = state.get("needs_rag", False)
        required = state.get("required_agents", [])

        if needs_rag or required:
            return "context_assembler"
        return "explainer"

    # Sequential chain: context → code → security → architecture → performance → explainer
    def route_after_context_sequential(state: AgentState) -> str:
        agents = state.get("required_agents") or []
        if "code_analysis" in agents:
            return "code_analyst"
        if "security_analysis" in agents:
            return "security_analyst"
        if "architecture_review" in agents:
            return "architecture_analyst"
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "explainer"

    def route_after_code(state: AgentState) -> str:
        agents = state.get("required_agents") or []
        if "security_analysis" in agents:
            return "security_analyst"
        if "architecture_review" in agents:
            return "architecture_analyst"
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "explainer"

    def route_after_security(state: AgentState) -> str:
        agents = state.get("required_agents") or []
        if "architecture_review" in agents:
            return "architecture_analyst"
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "explainer"

    def route_after_architecture(state: AgentState) -> str:
        agents = state.get("required_agents") or []
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "explainer"

    # Parallel: context → all analysts in parallel → explainer
    def route_after_context_parallel(state: AgentState) -> str:
        return "code_analyst"  # code_analyst node IS the _ParallelAnalystNode

    def route_after_parallel(state: AgentState) -> str:
        return "explainer"

    # ── Edges ──────────────────────────────────────────────────

    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "tool_executor": "tool_executor",
            "evidence_gatherer": "evidence_gatherer",
            "context_assembler": "context_assembler",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "tool_executor",
        route_after_tools,
        {
            "context_assembler": "context_assembler",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "evidence_gatherer",
        route_after_evidence,
        {
            "context_assembler": "context_assembler",
            "explainer": "explainer",
        },
    )

    if settings.enable_parallel_analysts:
        # Parallel mode: context → parallel_node → explainer
        builder.add_conditional_edges(
            "context_assembler",
            route_after_context_parallel,
            {"code_analyst": "code_analyst", "explainer": "explainer"},
        )
        builder.add_conditional_edges(
            "code_analyst",
            route_after_parallel,
            {"explainer": "explainer"},
        )
    else:
        # Sequential mode: context → code → security → architecture → performance → explainer
        builder.add_conditional_edges(
            "context_assembler",
            route_after_context_sequential,
            {
                "code_analyst": "code_analyst",
                "security_analyst": "security_analyst",
                "architecture_analyst": "architecture_analyst",
                "performance_analyst": "performance_analyst",
                "explainer": "explainer",
            },
        )
        builder.add_conditional_edges(
            "code_analyst",
            route_after_code,
            {
                "security_analyst": "security_analyst",
                "architecture_analyst": "architecture_analyst",
                "performance_analyst": "performance_analyst",
                "explainer": "explainer",
            },
        )
        builder.add_conditional_edges(
            "security_analyst",
            route_after_security,
            {
                "architecture_analyst": "architecture_analyst",
                "performance_analyst": "performance_analyst",
                "explainer": "explainer",
            },
        )
        builder.add_conditional_edges(
            "architecture_analyst",
            route_after_architecture,
            {
                "performance_analyst": "performance_analyst",
                "explainer": "explainer",
            },
        )
        builder.add_conditional_edges(
            "performance_analyst",
            lambda _: "explainer",
            {"explainer": "explainer"},
        )

    builder.add_edge("explainer", END)

    return builder.compile()
