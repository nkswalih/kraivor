"""Workspace-scoped tools for agentic data access.

Every tool receives (user_id, workspace_id) from AgentState — the LLM
never controls which workspace to query. This is the security boundary.
"""

from datetime import UTC, datetime

from app.infrastructure.service_client import ServiceClient


def _match_repo(repos: list[dict], name: str) -> dict | None:
    """Match a repo by name or full path (owner/repo)."""
    name_lower = name.lower()
    for r in repos:
        gh = (r.get("github_repo") or "").lower()
        if gh == name_lower or gh.endswith("/" + name_lower):
            return r
    for r in repos:
        gh = (r.get("github_repo") or "").lower()
        if name_lower in gh:
            return r
    return None


def _format_repos(repos: list[dict]) -> str:
    if not repos:
        return "No repositories found in this workspace."
    lines = [
        "## Repositories",
        "",
        "| Repo | Language | Score | Status | Last Analyzed |",
        "|------|----------|-------|--------|---------------|",
    ]
    for r in repos:
        gh = r.get("github_repo", "unknown")
        lang = r.get("language") or "—"
        score = r.get("last_analysis_score")
        score_str = f"{score}/100" if score is not None else "—"
        status = r.get("status", "connected")
        analyzed = (
            r.get("last_analyzed_at", "")[:10] if r.get("last_analyzed_at") else "—"
        )
        lines.append(f"| {gh} | {lang} | {score_str} | {status} | {analyzed} |")
    return "\n".join(lines)


def _format_report(report: dict) -> str:
    if not report:
        return "No analysis report available."
    score = report.get("overall_score", "—")
    parts = [f"**Overall Score:** {score}/100"]
    perf = report.get("performance_score")
    sec = report.get("security_score")
    rel = report.get("reliability_score")
    maint = report.get("maintainability_score")
    if any(v is not None for v in [perf, sec, rel, maint]):
        parts.append("")
        parts.append("| Category | Score |")
        parts.append("|----------|-------|")
        for label, val in [
            ("Security", sec),
            ("Performance", perf),
            ("Reliability", rel),
            ("Maintainability", maint),
        ]:
            parts.append(
                f"| {label} | {val}/100 |" if val is not None else f"| {label} | — |"
            )
    findings = report.get("total_findings")
    files = report.get("total_files")
    loc = report.get("total_lines_of_code")
    langs = report.get("languages_detected")
    details = []
    if findings is not None:
        details.append(f"{findings} total findings")
    if files is not None:
        details.append(f"{files} files")
    if loc is not None:
        details.append(f"{loc} lines of code")
    if langs:
        details.append(f"Languages: {', '.join(langs)}")
    if details:
        parts.append("")
        parts.append(" | ".join(details))
    return "\n".join(parts)


def _format_projects(projects: list[dict]) -> str:
    if not projects:
        return "No projects found in this workspace."
    lines = [
        "## Projects",
        "",
        "| Name | Status | Tasks | Blocked | Done |",
        "|------|--------|-------|---------|------|",
    ]
    for p in projects:
        name = p.get("name", "untitled")
        status = p.get("status", "—")
        total = p.get("task_count", 0)
        blocked = p.get("blocked_task_count", 0)
        done = p.get("done_task_count", 0)
        lines.append(f"| {name} | {status} | {total} | {blocked} | {done} |")
    return "\n".join(lines)


def _format_tasks(tasks: list[dict], project_name: str | None = None) -> str:
    if not tasks:
        return "No tasks found."
    lines = ["## Tasks"]
    if project_name:
        lines.append(f"Filtered by project: {project_name}")
    lines.append("")
    lines.append("| Title | Status | Priority | Assignee | Due |")
    lines.append("|-------|--------|----------|----------|-----|")
    for t in tasks:
        title = t.get("title", "untitled")[:60]
        status = t.get("status", "—")
        priority = t.get("priority", "—")
        assignee = t.get("assignee_id", "")[:8] if t.get("assignee_id") else "—"
        due = (t.get("due_date") or "")[:10] if t.get("due_date") else "—"
        lines.append(f"| {title} | {status} | {priority} | {assignee} | {due} |")
    return "\n".join(lines)


def _format_knowledge_spaces(spaces: list[dict]) -> str:
    if not spaces:
        return "No knowledge spaces found."
    lines = [
        "## Knowledge Spaces",
        "",
        "| Name | Description | Updated |",
        "|------|-------------|---------|",
    ]
    for s in spaces:
        name = s.get("name", "untitled")
        desc = (s.get("description") or "")[:60]
        updated = (s.get("updated_at") or "")[:10]
        lines.append(f"| {name} | {desc} | {updated} |")
    return "\n".join(lines)


def _format_notifications(notifications: list[dict]) -> str:
    if not notifications:
        return "No notifications."
    lines = [
        "## Notifications",
        "",
        "| Title | Type | Read | Created |",
        "|-------|------|------|---------|",
    ]
    for n in notifications:
        title = (n.get("title") or "untitled")[:60]
        ntype = n.get("type", "—")
        read = "✓" if n.get("is_read") else "○"
        created = (n.get("created_at") or "")[:10]
        lines.append(f"| {title} | {ntype} | {read} | {created} |")
    return "\n".join(lines)


def _format_discussions(discussions: list[dict]) -> str:
    if not discussions:
        return "No discussions found."
    lines = [
        "## Discussions",
        "",
        "| Title | Author | Comments | Created |",
        "|-------|--------|----------|---------|",
    ]
    for d in discussions:
        title = (d.get("title") or "untitled")[:60]
        author = (d.get("author") or {}).get("display_name", d.get("created_by", ""))[
            :20
        ]
        comments = d.get("comment_count", 0)
        created = (d.get("created_at") or "")[:10]
        lines.append(f"| {title} | {author} | {comments} | {created} |")
    return "\n".join(lines)


def _format_comments(comments: list[dict]) -> str:
    if not comments:
        return "No comments found."
    lines = ["## Comments", ""]
    for c in comments:
        author = (c.get("author") or {}).get("display_name", c.get("created_by", ""))[
            :20
        ]
        content = (c.get("content") or "")[:300]
        created = (c.get("created_at") or "")[:10]
        lines.append(f"**{author}** ({created}):")
        lines.append(f"> {content}")
        lines.append("")
    return "\n".join(lines)


class WorkspaceTools:
    def __init__(self, client: ServiceClient):
        self.client = client

    async def get_repos(self, user_id: str, workspace_id: str) -> str:
        repos = await self.client.get_repos(user_id, workspace_id)
        return _format_repos(repos)

    async def get_analysis_report(
        self, user_id: str, workspace_id: str, repo_name: str
    ) -> str:
        repos = await self.client.get_repos(user_id, workspace_id)
        repo = _match_repo(repos, repo_name)
        if not repo:
            return f"No repository found matching '{repo_name}' in your workspace."
        report = await self.client.get_analysis_report(
            user_id, workspace_id, repo["id"]
        )
        if not report:
            return f"Repository '{repo.get('github_repo', repo_name)}' has not been analyzed yet."
        result = _format_report(report)
        repo_info = f"**Repository:** {repo.get('github_repo', repo_name)}\n\n"
        return repo_info + result

    async def get_projects(self, user_id: str, workspace_id: str) -> str:
        projects = await self.client.get_projects(user_id, workspace_id)
        return _format_projects(projects)

    async def get_tasks(
        self,
        user_id: str,
        workspace_id: str,
        project_name: str | None = None,
        status: str | None = None,
    ) -> str:
        project_id = None
        if project_name:
            projects = await self.client.get_projects(user_id, workspace_id)
            for p in projects:
                if project_name.lower() in p.get("name", "").lower():
                    project_id = p["id"]
                    break
        tasks = await self.client.get_tasks(user_id, workspace_id, project_id)
        if status:
            tasks = [t for t in tasks if t.get("status", "").lower() == status.lower()]
        return _format_tasks(tasks, project_name)

    async def get_knowledge_spaces(self, user_id: str, workspace_id: str) -> str:
        spaces = await self.client.get_knowledge_spaces(user_id, workspace_id)
        return _format_knowledge_spaces(spaces)

    async def get_notifications(
        self, user_id: str, workspace_id: str, limit: int = 10
    ) -> str:
        notifications = await self.client.get_notifications(user_id, workspace_id)
        notifications = notifications[:limit]
        return _format_notifications(notifications)

    async def get_discussions(
        self, user_id: str, workspace_id: str, limit: int = 10, trending: bool = False
    ) -> str:
        discussions = await self.client.get_discussions(user_id, workspace_id)
        if trending:
            discussions = sorted(
                discussions, key=lambda d: d.get("comment_count", 0), reverse=True
            )
        discussions = discussions[:limit]
        return _format_discussions(discussions)

    async def get_discussion_comments(
        self, user_id: str, workspace_id: str, discussion_title: str, limit: int = 20
    ) -> str:
        discussions = await self.client.get_discussions(user_id, workspace_id)
        target = None
        for d in discussions:
            if discussion_title.lower() in (d.get("title", "")).lower():
                target = d
                break
        if not target:
            return f"No discussion found matching '{discussion_title}'."
        comments = await self.client.get_discussion_comments(
            user_id, workspace_id, target["id"]
        )
        comments = comments[:limit]
        return _format_comments(comments)

    async def get_current_date(self, user_id: str, workspace_id: str) -> str:
        now = datetime.now(UTC)
        return now.strftime("%A, %B %d, %Y — %H:%M %Z")

    async def web_search(
        self, user_id: str, workspace_id: str, query: str, max_results: int = 5
    ) -> str:
        from app.application.tools.search_tool import DuckDuckGoSearchTool

        tool = DuckDuckGoSearchTool()
        return await tool.run(query=query, max_results=max_results)

    async def web_fetch(self, user_id: str, workspace_id: str, url: str) -> str:
        from app.application.tools.web_fetch_tool import WebFetchTool

        tool = WebFetchTool()
        return await tool.run(url=url)

    async def remember_user_fact(
        self, user_id: str, workspace_id: str, fact_type: str, fact_key: str, fact_value: str
    ) -> str:
        from app.application.memory.user_memory_service import store_fact_explicit

        return await store_fact_explicit(user_id, fact_type, fact_key, fact_value)


# OpenAI function-calling tool definitions for the LLM.
# These schemas are sent with every tool_executor LLM call.
WORKSPACE_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_workspace_repos",
            "description": "List all repositories in the user's workspace with analysis scores. "
            "Call this when the user asks about repositories, code repos, "
            "or mentions a repo name they want information about.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_repo_analysis_report",
            "description": "Get the latest code analysis report for a specific repository. "
            "Includes scores (overall, security, performance, reliability, "
            "maintainability), total findings, languages detected, and stats.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "The repository name to get analysis for. "
                        "Can be just the name (e.g., 'ai-chatbox') "
                        "or full path (e.g., 'owner/ai-chatbox').",
                    }
                },
                "required": ["repo_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_workspace_projects",
            "description": "List all projects in the user's workspace with task counts "
            "and current status.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_project_tasks",
            "description": "List tasks, optionally filtered by project name or status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Project name to filter by (optional). "
                        "If omitted, returns all tasks.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["backlog", "todo", "in_progress", "in_review", "done"],
                        "description": "Filter by task status (optional).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_knowledge_spaces",
            "description": "List knowledge spaces (documentation and canvas spaces) "
            "in the workspace.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_notifications",
            "description": "Get recent notifications for the current user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of notifications to return (default 10).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_workspace_discussions",
            "description": "List discussions and community posts in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of discussions to return (default 10).",
                    },
                    "trending": {
                        "type": "boolean",
                        "description": "If true, return trending discussions sorted by activity.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_discussion_comments",
            "description": "Get comments for a specific discussion thread. Call "
            "get_workspace_discussions first to find discussion titles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "discussion_title": {
                        "type": "string",
                        "description": "The title or part of the title of the discussion "
                        "to get comments for.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of comments to return (default 20).",
                    },
                },
                "required": ["discussion_title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_date",
            "description": "Get the current date and time. Use this when the user asks "
            "about today's date, current time, or any time-related question.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using DuckDuckGo. Use this when the user asks "
            "about current events, latest news, recent information, or anything "
            "not available in your training data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find information about.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and extract text content from a URL. Use this to read "
            "the content of a specific webpage when you need detailed information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch content from.",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_user_fact",
            "description": "Store a fact about the user for future conversations. Use this "
            "when the user tells you something about themselves, their preferences, "
            "corrects you, or shares project context. This helps the AI learn about "
            "the user across sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact_type": {
                        "type": "string",
                        "enum": [
                            "identity",
                            "preference",
                            "tech_stack",
                            "correction",
                            "project_context",
                            "goal",
                        ],
                        "description": "The category of fact to store.",
                    },
                    "fact_key": {
                        "type": "string",
                        "description": "A short key for this fact (e.g., 'name', 'preferred_framework', 'project_deadline').",
                    },
                    "fact_value": {
                        "type": "string",
                        "description": "The value of the fact to remember.",
                    },
                },
                "required": ["fact_type", "fact_key", "fact_value"],
            },
        },
    },
]
