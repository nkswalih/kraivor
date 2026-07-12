import json

import logging

from app.application.agents.prompts.tool_executor import TOOL_EXECUTOR_PROMPT
from app.application.provisioning.key_resolver import KeyResolver
from app.application.tools.workspace_tools import (
    WORKSPACE_TOOL_DEFINITIONS,
    WorkspaceTools,
)
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.router import ModelRouter

logger = logging.getLogger(__name__)


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
            "web_fetch": self.tools.web_fetch,
            "remember_user_fact": self.tools.remember_user_fact,
        }

    async def __call__(self, state: dict) -> dict:
        user_id = state.get("user_id", "")
        user_name = state.get("user_name")
        user_context = state.get("user_context")
        workspace_id = state.get("workspace_id", "")
        message = state.get("message", "")
        history = state.get("context_history") or []
        route = self.router.get_route("tool_calling")
        api_key, provider = await self.key_resolver.resolve(user_id, route["model"])
        client = LLMClient(api_key=api_key, provider=provider, model=route["model"])

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
            response = await client.generate(
                messages,
                tools=WORKSPACE_TOOL_DEFINITIONS,
                max_tokens=route["max_tokens"],
                tool_choice="auto",
            )

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
                executor = self._tool_map.get(pc["name"])
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
