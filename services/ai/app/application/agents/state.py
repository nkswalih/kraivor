from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    user_id: str
    user_name: str | None
    workspace_id: str
    message: str
    conversation_id: str | None
    repo_ids: list[str] | None
    model: str | None
    stream: bool

    intent: str | None
    complexity: str | None
    required_agents: list[str] | None
    context_hints: list[str] | None
    needs_rag: bool
    needs_tools: bool

    context_code: list[dict] | None
    context_analysis: list[dict] | None
    context_history: list[dict] | None
    assembled_context: str | None
    user_context: str | None

    messages: Annotated[list, add_messages]
    tool_results: str | None
    tool_calls: list[dict]
    sources: list[dict]

    code_findings: list[dict] | None
    security_findings: list[dict] | None
    architecture_findings: list[dict] | None
    performance_findings: list[dict] | None

    evidence: str | None
    evidence_sources: list[dict] | None
    needs_evidence: bool

    low_confidence: bool
    parallel: bool

    response: str | None
    usage: dict | None

    # Provider error propagation — set by nodes when LLM calls fail.
    # Allows downstream nodes (especially explainer) to degrade gracefully.
    provider_error: str | None
    provider_error_category: str | None  # ErrorCategory value
    provider_error_details: dict | None  # {category, provider, suggested_action, retry_after}
