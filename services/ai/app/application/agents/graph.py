from langgraph.graph import StateGraph, END
from app.application.agents.state import AgentState
from app.application.agents.orchestrator import OrchestratorNode
from app.application.agents.code_analyst import CodeAnalystNode
from app.application.agents.security import SecurityAnalystNode
from app.application.agents.architecture import ArchitectureAnalystNode
from app.application.agents.performance import PerformanceAnalystNode
from app.application.agents.context_assembler import ContextAssemblerNode
from app.application.agents.explainer import ExplainerNode


def build_agent_graph() -> StateGraph:
    builder = StateGraph(AgentState)

    builder.add_node("orchestrator", OrchestratorNode())
    builder.add_node("context_assembler", ContextAssemblerNode())
    builder.add_node("code_analyst", CodeAnalystNode())
    builder.add_node("security_analyst", SecurityAnalystNode())
    builder.add_node("architecture_analyst", ArchitectureAnalystNode())
    builder.add_node("performance_analyst", PerformanceAnalystNode())
    builder.add_node("explainer", ExplainerNode())

    builder.set_entry_point("orchestrator")

    def route_after_orchestrator(state: AgentState) -> str:
        """Route based on orchestrator output.
        - If response is already set (direct intent), go to END.
        - If only code review without RAG, go to explainer.
        - If RAG is needed, go to context_assembler.
        """
        response = state.get("response")
        if response:
            return "end"

        required = state.get("required_agents", [])
        needs_rag = state.get("needs_rag", False)

        if needs_rag:
            return "context_assembler"
        if required:
            return "context_assembler"
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
