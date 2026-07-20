import logging

from langgraph.graph import END, StateGraph

from app.application.agents.architecture import ArchitectureAnalystNode
from app.application.agents.code_analyst import CodeAnalystNode
from app.application.agents.context_assembler import ContextAssemblerNode
from app.application.agents.evidence_gatherer import EvidenceGathererNode
from app.application.agents.orchestrator import OrchestratorNode
from app.application.agents.performance import PerformanceAnalystNode
from app.application.agents.security import SecurityAnalystNode
from app.application.agents.state import AgentState
from app.application.agents.tool_executor import ToolExecutorNode
from app.application.tools.workspace_tools import WorkspaceTools

logger = logging.getLogger(__name__)


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
    builder.add_node("code_analyst", CodeAnalystNode())
    builder.add_node("security_analyst", SecurityAnalystNode())
    builder.add_node("architecture_analyst", ArchitectureAnalystNode())
    builder.add_node("performance_analyst", PerformanceAnalystNode())

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
        return "end"

    # Fix 1: context_assembler fans out to ALL analysts. Each analyst checks
    # if it's in required_agents and skips (returns empty findings) if not.
    # This eliminates the sequential code→security→architecture→performance chain.
    def route_after_context(state: AgentState) -> str:
        agents = state.get("required_agents") or []
        # Always route to code_analyst first — it will skip if not required.
        if "code_analysis" in agents:
            return "code_analyst"
        if "security_analysis" in agents:
            return "security_analyst"
        if "architecture_review" in agents:
            return "architecture_analyst"
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "end"

    def route_after_code(state: AgentState) -> str:
        agents = state.get("required_agents") or []
        if "security_analysis" in agents:
            return "security_analyst"
        if "architecture_review" in agents:
            return "architecture_analyst"
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "end"

    def route_after_security(state: AgentState) -> str:
        agents = state.get("required_agents") or []
        if "architecture_review" in agents:
            return "architecture_analyst"
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "end"

    def route_after_architecture(state: AgentState) -> str:
        agents = state.get("required_agents") or []
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "end"

    def route_after_performance(state: AgentState) -> str:
        return "end"

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
            "end": END,
        },
    )

    # Fix 1: context_assembler → first required analyst (fan-out pattern)
    builder.add_conditional_edges(
        "context_assembler",
        route_after_context,
        {
            "code_analyst": "code_analyst",
            "security_analyst": "security_analyst",
            "architecture_analyst": "architecture_analyst",
            "performance_analyst": "performance_analyst",
            "end": END,
        },
    )

    # Each analyst routes to the next required analyst or END
    builder.add_conditional_edges(
        "code_analyst",
        route_after_code,
        {
            "security_analyst": "security_analyst",
            "architecture_analyst": "architecture_analyst",
            "performance_analyst": "performance_analyst",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "security_analyst",
        route_after_security,
        {
            "architecture_analyst": "architecture_analyst",
            "performance_analyst": "performance_analyst",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "architecture_analyst",
        route_after_architecture,
        {
            "performance_analyst": "performance_analyst",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "performance_analyst",
        route_after_performance,
        {"end": END},
    )

    return builder.compile()
