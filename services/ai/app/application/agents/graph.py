from langgraph.graph import StateGraph, END
from app.application.agents.state import AgentState
from app.application.agents.orchestrator import OrchestratorNode
from app.application.agents.tool_executor import ToolExecutorNode
from app.application.tools.workspace_tools import WorkspaceTools
from app.application.agents.code_analyst import CodeAnalystNode
from app.application.agents.security import SecurityAnalystNode
from app.application.agents.architecture import ArchitectureAnalystNode
from app.application.agents.performance import PerformanceAnalystNode
from app.application.agents.context_assembler import ContextAssemblerNode
from app.application.agents.explainer import ExplainerNode


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

    builder.add_node("context_assembler", ContextAssemblerNode())
    builder.add_node("code_analyst", CodeAnalystNode())
    builder.add_node("security_analyst", SecurityAnalystNode())
    builder.add_node("architecture_analyst", ArchitectureAnalystNode())
    builder.add_node("performance_analyst", PerformanceAnalystNode())
    builder.add_node("explainer", ExplainerNode())

    builder.set_entry_point("orchestrator")

    def route_after_orchestrator(state: AgentState) -> str:
        if state.get("response"):
            return "end"

        needs_tools = state.get("needs_tools", False)
        needs_rag = state.get("needs_rag", False)
        required = state.get("required_agents", [])

        if needs_tools:
            return "tool_executor"
        if needs_rag or required:
            return "context_assembler"
        return "explainer"

    def route_after_tools(state: AgentState) -> str:
        if state.get("response"):
            return "end"

        needs_rag = state.get("needs_rag", False)
        required = state.get("required_agents", [])

        if needs_rag or required:
            return "context_assembler"

        tool_results = state.get("tool_results")
        if tool_results:
            return "explainer"
        return "explainer"

    def route_after_context(state: AgentState) -> str:
        agents = state.get("required_agents", [])
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
        agents = state.get("required_agents", [])
        if "security_analysis" in agents:
            return "security_analyst"
        if "architecture_review" in agents:
            return "architecture_analyst"
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "explainer"

    def route_after_security(state: AgentState) -> str:
        agents = state.get("required_agents", [])
        if "architecture_review" in agents:
            return "architecture_analyst"
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "explainer"

    def route_after_architecture(state: AgentState) -> str:
        agents = state.get("required_agents", [])
        if "performance_analysis" in agents:
            return "performance_analyst"
        return "explainer"

    def route_after_performance(state: AgentState) -> str:
        return "explainer"

    builder.add_conditional_edges("orchestrator", route_after_orchestrator, {
        "tool_executor": "tool_executor",
        "context_assembler": "context_assembler",
        "explainer": "explainer",
        "end": END,
    })
    builder.add_conditional_edges("tool_executor", route_after_tools, {
        "context_assembler": "context_assembler",
        "explainer": "explainer",
        "end": END,
    })
    builder.add_conditional_edges("context_assembler", route_after_context)
    builder.add_conditional_edges("code_analyst", route_after_code)
    builder.add_conditional_edges("security_analyst", route_after_security)
    builder.add_conditional_edges("architecture_analyst", route_after_architecture)
    builder.add_conditional_edges("performance_analyst", route_after_performance)
    builder.add_edge("explainer", END)

    return builder.compile()
