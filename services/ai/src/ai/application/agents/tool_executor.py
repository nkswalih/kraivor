import json

import logging

from app.application.agents.prompts.tool_executor import TOOL_EXECUTOR_PROMPT
from app.application.provisioning.key_resolver import KeyResolver
from app.application.tools.workspace_tools import (
    WORKSPACE_TOOL_DEFINITIONS,
    WorkspaceTools,
)
from app.infrastructure.llm.client import LLM_SHORT_TIMEOUT
from app.infrastructure.llm.failover_engine import FailoverEngine
from app.infrastructure.llm.router import ModelRouter

logger = logging.getLogger(__name__)

# Fix 7: Tools that write to persistent memory — guard against prompt injection.
_MEMORY_WRITE_TOOLS = frozenset({
    "remember_user_fact",
    "store_knowledge",
    "submit_feedback",
    "deduplicate_knowledge",
})

_INJECTION_PHRASES = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard prior",
    "disregard previous",
    "new instructions:",
    "system prompt:",
    "you are now",
    "act as if",
    "pretend you are",
    "forget everything",
    "override instructions",
)


def _is_safe_for_memory_write(tool_name: str, args: dict) -> bool:
    """Reject memory-write tool calls that contain prompt injection phrases."""
    if tool_name not in _MEMORY_WRITE_TOOLS:
        return True
    text = " ".join(str(v) for v in args.values()).lower()
    for phrase in _INJECTION_PHRASES:
        if phrase in text:
            logger.warning(
                "Blocked memory-write tool '%s' — injection phrase detected: '%s'",
                tool_name, phrase,
            )
            return False
    return True


def _format_prompt(
    template: str, user_name: str | None, user_context: str | None
) -> str:
    name = user_name or "the user"
    ctx = f"Known context about the user:\n{user_context}" if user_context else ""
    return template.format(user_name=name, user_context=ctx)


class ToolExecutorNode:
    def __init__(self, workspace_tools: WorkspaceTools):
        self.tools = workspace_tools
        self.router = ModelRouter()
        self.key_resolver = KeyResolver()
        self.failover = FailoverEngine(self.key_resolver)
        self._tool_map = {
            "get_workspace_repos": self.tools.get_repos,
            "get_repo_analysis_report": self.tools.get_analysis_report,
            "get_workspace_projects": self.tools.get_projects,
            "get_project_tasks": self.tools.get_tasks,
            "get_knowledge_spaces": self.tools.get_knowledge_spaces,
            "get_user_notifications": self.tools.get_notifications,
            "get_workspace_discussions": self.tools.get_discussions,
            "get_discussion_comments": self.tools.get_discussion_comments,
            "get_current_date": self.tools.get_current_date,
            "web_search": self.tools.web_search,
            "web_search_news": self.tools.web_search_news,
            "web_search_instant": self.tools.web_search_instant,
            "web_fetch": self.tools.web_fetch,
            "browse_web": self.tools.browse_web,
            "remember_user_fact": self.tools.remember_user_fact,
            "research_topic": self.tools.research_topic,
            "verify_fact": self.tools.verify_fact,
            "get_documentation": self.tools.get_documentation,
            "get_github_info": self.tools.get_github_info,
            "search_knowledge": self.tools.search_knowledge,
            "store_knowledge": self.tools.store_knowledge,
            "get_knowledge_stats": self.tools.get_knowledge_stats,
            "get_entity_graph": self.tools.get_entity_graph,
            "get_top_entities": self.tools.get_top_entities,
            "run_proactive_learning": self.tools.run_proactive_learning,
            "summarize_knowledge": self.tools.summarize_knowledge,
            "resolve_conflicts": self.tools.resolve_conflicts,
            "submit_feedback": self.tools.submit_feedback,
            "deduplicate_knowledge": self.tools.deduplicate_knowledge,
            "export_knowledge": self.tools.export_knowledge,
            "knowledge_health": self.tools.knowledge_health,
        }

    async def __call__(self, state: dict) -> dict:
        user_id = state.get("user_id", "")
        user_name = state.get("user_name")
        user_context = state.get("user_context")
        workspace_id = state.get("workspace_id", "")
        message = state.get("message", "")
        user_model = state.get("model")
        history = state.get("context_history") or []
        auth_token = state.get("auth_token")
        route = self.router.get_route_for_user("tool_calling", user_model)

        # Create per-request WorkspaceTools with auth_token for safe concurrent access
        tools = WorkspaceTools(self.tools.client, auth_token=auth_token)
        tool_map = {
            "get_workspace_repos": tools.get_repos,
            "get_repo_analysis_report": tools.get_analysis_report,
            "get_workspace_projects": tools.get_projects,
            "get_project_tasks": tools.get_tasks,
            "get_knowledge_spaces": tools.get_knowledge_spaces,
            "get_user_notifications": tools.get_notifications,
            "get_workspace_discussions": tools.get_discussions,
            "get_discussion_comments": tools.get_discussion_comments,
            "get_current_date": tools.get_current_date,
            "web_search": tools.web_search,
            "web_search_news": tools.web_search_news,
            "web_search_instant": tools.web_search_instant,
            "web_fetch": tools.web_fetch,
            "browse_web": tools.browse_web,
            "remember_user_fact": tools.remember_user_fact,
            "research_topic": tools.research_topic,
            "verify_fact": tools.verify_fact,
            "get_documentation": tools.get_documentation,
            "get_github_info": tools.get_github_info,
            "search_knowledge": tools.search_knowledge,
            "store_knowledge": tools.store_knowledge,
            "get_knowledge_stats": tools.get_knowledge_stats,
            "get_entity_graph": tools.get_entity_graph,
            "get_top_entities": tools.get_top_entities,
            "run_proactive_learning": tools.run_proactive_learning,
            "summarize_knowledge": tools.summarize_knowledge,
            "resolve_conflicts": tools.resolve_conflicts,
            "submit_feedback": tools.submit_feedback,
            "deduplicate_knowledge": tools.deduplicate_knowledge,
            "export_knowledge": tools.export_knowledge,
            "knowledge_health": tools.knowledge_health,
        }

        messages = [
            {
                "role": "system",
                "content": _format_prompt(
                    TOOL_EXECUTOR_PROMPT, user_name, user_context
                ),
            }
        ]
        for h in history[-5:]:
            role = h.get("role", "user")
            content = h.get("content", "")
            messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        recorded_calls = []

        for _round_num in range(3):
            try:
                response = await self.failover.execute(
                    messages, user_id, route,
                    tools=WORKSPACE_TOOL_DEFINITIONS,
                    max_tokens=route["max_tokens"],
                    tool_choice="auto",
                    timeout=LLM_SHORT_TIMEOUT,
                )
            except Exception as e:
                logger.error("tool_executor LLM call failed: %s", e)
                return {
                    "tool_results": "I'm having trouble processing your request. Please try again.",
                    "tool_calls": recorded_calls,
                    "response": "I'm having trouble processing your request. Please try again.",
                }

            tool_calls = response.get("tool_calls", [])
            content = response.get("content") or ""

            if content and not tool_calls:
                return {
                    "tool_results": content,
                    "tool_calls": recorded_calls,
                    "response": content,
                }

            if not tool_calls:
                return {
                    "tool_results": content
                    or "I couldn't find an answer to that question.",
                    "tool_calls": recorded_calls,
                    "response": content
                    or "I couldn't find an answer to that question.",
                }

            # 1) Parse tool calls from the model response
            parsed_calls = []
            for tc in tool_calls:
                tc_id = tc.id if hasattr(tc, "id") else tc.get("id", "")
                fn_name = (
                    tc.function.name
                    if hasattr(tc, "function")
                    else tc.get("function", {}).get("name", "")
                )
                fn_args_raw = (
                    tc.function.arguments
                    if hasattr(tc, "function")
                    else tc.get("function", {}).get("arguments", "{}")
                )
                if isinstance(fn_args_raw, str):
                    try:
                        fn_args = json.loads(fn_args_raw)
                    except json.JSONDecodeError:
                        fn_args = {}
                else:
                    fn_args = fn_args_raw
                parsed_calls.append(
                    {
                        "id": tc_id,
                        "name": fn_name,
                        "args": fn_args,
                        "args_raw": (
                            fn_args_raw
                            if isinstance(fn_args_raw, str)
                            else json.dumps(fn_args_raw)
                        ),
                    }
                )

            # 2) Execute all tools
            tool_results = []
            for pc in parsed_calls:
                recorded_calls.append({"name": pc["name"], "arguments": pc["args"]})

                # Fix 7: Guard memory-write tools against prompt injection
                if not _is_safe_for_memory_write(pc["name"], pc["args"]):
                    tool_results.append({
                        "id": pc["id"],
                        "name": pc["name"],
                        "result": "Tool call rejected: content contains suspicious instructions.",
                    })
                    continue

                executor = tool_map.get(pc["name"])
                if executor:
                    try:
                        result_str = await executor(
                            user_id=user_id, workspace_id=workspace_id, **pc["args"]
                        )
                    except Exception as e:
                        logger.error("Tool %s failed: %s", pc["name"], e)
                        result_str = f"Error executing {pc['name']}: {e}"
                else:
                    result_str = f"Tool '{pc['name']}' is not available."
                tool_results.append(
                    {"id": pc["id"], "name": pc["name"], "result": result_str}
                )

            # 3) Append assistant message with tool_calls (required by OpenAI)
            assistant_msg = {
                "role": "assistant",
                "content": content or None,
                "tool_calls": [
                    {
                        "id": pc["id"],
                        "type": "function",
                        "function": {"name": pc["name"], "arguments": pc["args_raw"]},
                    }
                    for pc in parsed_calls
                ],
            }
            messages.append(assistant_msg)

            # 4) Append tool role messages with results
            for tr in tool_results:
                messages.append(
                    {"role": "tool", "tool_call_id": tr["id"], "content": tr["result"]}
                )

        return {
            "tool_results": "I reached the maximum number of tool calls. Please try rephrasing your question.",
            "tool_calls": recorded_calls,
            "response": "I reached the maximum number of tool calls. Please try rephrasing your question.",
        }
