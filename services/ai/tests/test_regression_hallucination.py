"""Regression tests for the three real-world hallucination failures.

Tests that the AI Agent chat pipeline correctly:
1. Routes 'mythos vs kraivor ai' through evidence gathering (not direct response with severity table)
2. Routes 'what is kraivor?' through evidence gathering (not direct response with invented paths)
3. Routes 'kraivor ai using model' through evidence gathering (not direct response with audit findings)
"""

import pytest


class TestOrchestratorIntentRouting:
    """Verify that knowledge-intensive intents route through evidence gathering."""

    def test_question_intent_has_needs_evidence(self):
        from app.application.agents.orchestrator import _EVIDENCE_INTENTS, _DIRECT_INTENTS
        assert "question" in _EVIDENCE_INTENTS
        assert "question" not in _DIRECT_INTENTS

    def test_programming_intent_has_needs_evidence(self):
        from app.application.agents.orchestrator import _EVIDENCE_INTENTS, _DIRECT_INTENTS
        assert "programming" in _EVIDENCE_INTENTS
        assert "programming" not in _DIRECT_INTENTS

    def test_documentation_intent_has_needs_evidence(self):
        from app.application.agents.orchestrator import _EVIDENCE_INTENTS, _DIRECT_INTENTS
        assert "documentation" in _EVIDENCE_INTENTS
        assert "documentation" not in _DIRECT_INTENTS

    def test_code_generation_routes_through_evidence(self):
        from app.application.agents.orchestrator import _EVIDENCE_INTENTS, _DIRECT_INTENTS
        assert "code_generation" in _EVIDENCE_INTENTS
        assert "code_generation" not in _DIRECT_INTENTS

    def test_writing_routes_through_evidence(self):
        from app.application.agents.orchestrator import _EVIDENCE_INTENTS, _DIRECT_INTENTS
        assert "writing" in _EVIDENCE_INTENTS
        assert "writing" not in _DIRECT_INTENTS

    def test_greeting_remains_direct(self):
        from app.application.agents.orchestrator import _DIRECT_INTENTS
        assert "greeting" in _DIRECT_INTENTS

    def test_conversation_remains_direct(self):
        from app.application.agents.orchestrator import _DIRECT_INTENTS
        assert "conversation" in _DIRECT_INTENTS

    def test_unknown_remains_direct(self):
        from app.application.agents.orchestrator import _DIRECT_INTENTS
        assert "unknown" in _DIRECT_INTENTS

    def test_workspace_query_not_in_evidence_intents(self):
        from app.application.agents.orchestrator import _EVIDENCE_INTENTS
        assert "workspace_query" not in _EVIDENCE_INTENTS


class TestGraphRouting:
    """Verify the graph routes through evidence_gatherer for evidence intents."""

    def test_graph_has_evidence_gatherer_node(self):
        from app.application.agents.graph import build_agent_graph
        graph = build_agent_graph(client=None)
        node_names = [n for n in graph.get_graph().nodes]
        assert "evidence_gatherer" in node_names

    def test_graph_has_all_nodes(self):
        from app.application.agents.graph import build_agent_graph
        graph = build_agent_graph(client=None)
        node_names = [n for n in graph.get_graph().nodes]
        expected = ["orchestrator", "tool_executor", "evidence_gatherer",
                     "context_assembler", "explainer"]
        for name in expected:
            assert name in node_names, f"Missing node: {name}"


class TestExplainerPromptSelection:
    """Verify that the explainer selects the right prompt for the right intent."""

    def test_select_prompt_for_casual(self):
        from app.application.agents.explainer import _select_prompt, EXPLAINER_CASUAL_PROMPT
        result = _select_prompt("greeting", False, False, False)
        assert result == EXPLAINER_CASUAL_PROMPT

    def test_select_prompt_for_audit_with_findings(self):
        from app.application.agents.explainer import _select_prompt, EXPLAINER_CODE_AUDIT_PROMPT
        result = _select_prompt("repository_analysis", True, False, False)
        assert result == EXPLAINER_CODE_AUDIT_PROMPT

    def test_select_prompt_for_question_with_evidence(self):
        from app.application.agents.explainer import _select_prompt, EXPLAINER_EVIDENCE_PROMPT
        result = _select_prompt("question", False, True, False)
        assert result == EXPLAINER_EVIDENCE_PROMPT

    def test_select_prompt_for_question_with_user_context(self):
        """KEY TEST: 'what is kraivor?' with user_context should use GENERAL_QA, not audit."""
        from app.application.agents.explainer import _select_prompt, EXPLAINER_GENERAL_QA_PROMPT
        result = _select_prompt("question", False, False, True)
        assert result == EXPLAINER_GENERAL_QA_PROMPT

    def test_select_prompt_for_question_without_any_context(self):
        from app.application.agents.explainer import _select_prompt, EXPLAINER_SYSTEM_PROMPT
        result = _select_prompt("question", False, False, False)
        assert result == EXPLAINER_SYSTEM_PROMPT

    def test_select_prompt_for_unknown_intent(self):
        from app.application.agents.explainer import _select_prompt, EXPLAINER_SYSTEM_PROMPT
        result = _select_prompt(None, False, False, False)
        assert result == EXPLAINER_SYSTEM_PROMPT

    def test_select_prompt_evidence_takes_priority_over_user_context(self):
        from app.application.agents.explainer import _select_prompt, EXPLAINER_EVIDENCE_PROMPT
        result = _select_prompt("question", False, True, True)
        assert result == EXPLAINER_EVIDENCE_PROMPT

    def test_select_prompt_audit_findings_takes_priority_over_evidence(self):
        from app.application.agents.explainer import _select_prompt, EXPLAINER_CODE_AUDIT_PROMPT
        result = _select_prompt("repository_analysis", True, True, True)
        assert result == EXPLAINER_CODE_AUDIT_PROMPT


class TestStateHasEvidenceFields:
    """Verify AgentState has the new evidence fields."""

    def test_agent_state_has_evidence(self):
        from app.application.agents.state import AgentState
        assert "evidence" in AgentState.__annotations__

    def test_agent_state_has_evidence_sources(self):
        from app.application.agents.state import AgentState
        assert "evidence_sources" in AgentState.__annotations__

    def test_agent_state_has_needs_evidence(self):
        from app.application.agents.state import AgentState
        assert "needs_evidence" in AgentState.__annotations__


class TestPromptsExist:
    """Verify all prompt templates exist and are non-empty."""

    def test_general_qa_prompt_exists(self):
        from app.application.agents.prompts.specialist import EXPLAINER_GENERAL_QA_PROMPT
        assert EXPLAINER_GENERAL_QA_PROMPT
        assert "{user_name}" in EXPLAINER_GENERAL_QA_PROMPT
        assert "{user_context}" in EXPLAINER_GENERAL_QA_PROMPT

    def test_evidence_prompt_has_user_context_instruction(self):
        from app.application.agents.prompts.specialist import EXPLAINER_EVIDENCE_PROMPT
        assert "PRIMARY source" in EXPLAINER_EVIDENCE_PROMPT

    def test_system_prompt_no_forced_severity_table(self):
        """EXPLAINER_SYSTEM_PROMPT should NOT force severity tables — only mention them conditionally."""
        from app.application.agents.prompts.specialist import EXPLAINER_SYSTEM_PROMPT
        # Should not have "Include a severity table at the top" (the old forced instruction)
        assert "include a severity table at the top" not in EXPLAINER_SYSTEM_PROMPT.lower()
        # Should mention severity tables only as conditional ("only use when...")
        assert "only use severity tables" in EXPLAINER_SYSTEM_PROMPT.lower()

    def test_audit_prompt_still_has_severity_table(self):
        """EXPLAINER_CODE_AUDIT_PROMPT should still have severity tables."""
        from app.application.agents.prompts.specialist import EXPLAINER_CODE_AUDIT_PROMPT
        assert "severity" in EXPLAINER_CODE_AUDIT_PROMPT.lower()
