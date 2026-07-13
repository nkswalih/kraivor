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
        self,
        user_id: str,
        workspace_id: str,
        query: str,
        max_results: int = 5,
        timelimit: str | None = None,
    ) -> str:
        from app.application.tools.search_tool import DuckDuckGoSearchTool

        tool = DuckDuckGoSearchTool()
        return await tool.run(query=query, max_results=max_results, timelimit=timelimit)

    async def web_search_news(
        self,
        user_id: str,
        workspace_id: str,
        query: str,
        max_results: int = 5,
        timelimit: str = "d",
    ) -> str:
        from app.application.tools.search_tool import DuckDuckGoNewsTool

        tool = DuckDuckGoNewsTool()
        return await tool.run(query=query, max_results=max_results, timelimit=timelimit)

    async def web_search_instant(
        self, user_id: str, workspace_id: str, query: str
    ) -> str:
        from app.application.tools.search_tool import DuckDuckGoInstantTool

        tool = DuckDuckGoInstantTool()
        return await tool.run(query=query)

    async def web_fetch(self, user_id: str, workspace_id: str, url: str) -> str:
        from app.application.tools.web_fetch_tool import WebFetchTool

        tool = WebFetchTool()
        return await tool.run(url=url)

    async def browse_web(
        self, user_id: str, workspace_id: str, url: str, question: str | None = None
    ) -> str:
        from app.application.tools.web_fetch_tool import WebFetchTool

        tool = WebFetchTool()
        content = await tool.run(url=url)
        if question and content and not content.startswith("Failed"):
            return f"Page content from {url}:\n\n{content}\n\nUser's question: {question}"
        return content

    async def remember_user_fact(
        self, user_id: str, workspace_id: str, fact_type: str, fact_key: str, fact_value: str
    ) -> str:
        from app.application.memory.user_memory_service import store_fact_explicit

        return await store_fact_explicit(user_id, fact_type, fact_key, fact_value)

    async def research_topic(
        self,
        user_id: str,
        workspace_id: str,
        query: str,
        max_sources: int = 5,
    ) -> str:
        """Deep research using the Knowledge Engine — searches multiple sources,
        ranks by trust/relevance, builds verified context with citations.
        Automatically stores results for future retrieval."""
        from app.knowledge_engine.engine import KnowledgeEngine

        engine = KnowledgeEngine()
        result = await engine.research_with_memory(
            query=query,
            workspace_id=workspace_id,
            max_sources=max_sources,
        )
        return result.context

    async def search_knowledge(
        self,
        user_id: str,
        workspace_id: str,
        query: str,
        top_k: int = 5,
    ) -> str:
        """Search previously stored knowledge. Use this BEFORE doing a fresh web
        search — the knowledge base may already have relevant information from
        previous research sessions."""
        from app.knowledge_engine.engine import KnowledgeEngine

        engine = KnowledgeEngine()
        results = await engine.retrieve_knowledge(workspace_id, query, top_k=top_k)

        if not results:
            return "No previously stored knowledge found for this query. Use research_topic to find fresh information."

        lines = ["## Previously Stored Knowledge", ""]
        for i, item in enumerate(results, 1):
            score = item.get("similarity", 0)
            lines.append(f"### [{i}] {item['title']}")
            lines.append(f"**Source:** {item['provider']} | **Relevance:** {score:.2f}")
            lines.append(f"**URL:** {item['source']}")
            if item.get("summary"):
                lines.append(f"**Summary:** {item['summary'][:200]}")
            content = item.get("content", "")[:1500]
            lines.append(f"\n{content}")
            lines.append("")

        return "\n".join(lines)

    async def store_knowledge(
        self,
        user_id: str,
        workspace_id: str,
        url: str,
        title: str,
        content: str,
        provider: str = "manual",
        summary: str | None = None,
    ) -> str:
        """Manually store a piece of knowledge (URL, title, content) into the
        persistent knowledge base for future retrieval."""
        from app.knowledge_engine.engine import KnowledgeEngine

        engine = KnowledgeEngine()
        item_id = await engine.store_knowledge(
            workspace_id=workspace_id,
            source_url=url,
            source_provider=provider,
            title=title,
            content=content,
            trust_score=0.7,
            summary=summary,
        )
        return f"Knowledge stored successfully. ID: {item_id}"

    async def get_knowledge_stats(
        self,
        user_id: str,
        workspace_id: str,
    ) -> str:
        """Get statistics about the stored knowledge base for this workspace."""
        from app.knowledge_engine.engine import KnowledgeEngine

        engine = KnowledgeEngine()
        stats = await engine.get_knowledge_stats(workspace_id)

        lines = [
            "## Knowledge Base Statistics",
            "",
            f"**Total items:** {stats['total_items']}",
            f"**Unique sources:** {stats['unique_urls']}",
            f"**Providers used:** {stats['providers']}",
            f"**Average trust score:** {stats['avg_trust']}",
        ]

        if stats.get("oldest"):
            lines.append(f"**Oldest entry:** {stats['oldest'][:10]}")
        if stats.get("newest"):
            lines.append(f"**Newest entry:** {stats['newest'][:10]}")

        return "\n".join(lines)

    async def get_entity_graph(
        self,
        user_id: str,
        workspace_id: str,
        entity_name: str,
        max_depth: int = 2,
    ) -> str:
        """Find entities related to a given technology or concept via the knowledge graph.
        Shows how technologies in the workspace connect to each other."""
        from app.knowledge_engine.graph.knowledge_graph import KnowledgeGraph

        graph = KnowledgeGraph()
        await graph.ensure_tables()
        related = await graph.find_related(workspace_id, entity_name, max_depth)

        if not related:
            return f"No related entities found for '{entity_name}' in the knowledge graph."

        lines = [f"## Related to: {entity_name}", ""]
        for r in related:
            lines.append(f"- **{r['relationship']}** {r['entity']} (strength: {r['weight']})")

        return "\n".join(lines)

    async def get_top_entities(
        self,
        user_id: str,
        workspace_id: str,
        entity_type: str | None = None,
    ) -> str:
        """Get the most mentioned technologies and concepts in the workspace knowledge base."""
        from app.knowledge_engine.graph.knowledge_graph import KnowledgeGraph

        graph = KnowledgeGraph()
        await graph.ensure_tables()
        entities = await graph.get_workspace_entities(workspace_id, entity_type, top_n=15)

        if not entities:
            return "No entities found in the knowledge graph yet."

        lines = ["## Top Entities in Knowledge Base", ""]
        for e in entities:
            lines.append(f"- **{e['name']}** ({e['type']}) — {e['mentions']} mentions")

        return "\n".join(lines)

    async def run_proactive_learning(
        self,
        user_id: str,
        workspace_id: str,
    ) -> str:
        """Run a proactive learning cycle — detect technologies used, check for
        new releases, security advisories, and auto-index relevant updates."""
        from app.knowledge_engine.learning.proactive_agent import ProactiveLearningPipeline

        pipeline = ProactiveLearningPipeline()
        result = await pipeline.run_full_cycle(workspace_id)

        lines = [
            "## Proactive Learning Results",
            "",
            f"**Technologies detected:** {', '.join(result['technologies']) if result['technologies'] else 'none'}",
            f"**New releases indexed:** {result['new_releases']}",
            f"**Security advisories:** {result['security_advisories']}",
            f"**Stale docs found:** {result['stale_docs']}",
            f"**Items indexed:** {result['items_indexed']}",
        ]

        return "\n".join(lines)

    async def verify_fact(
        self,
        user_id: str,
        workspace_id: str,
        claim: str,
    ) -> str:
        """Cross-check a claim across multiple trusted sources to verify accuracy."""
        from app.knowledge_engine.engine import KnowledgeEngine

        engine = KnowledgeEngine()
        result = await engine.research(
            claim,
            max_sources=5,
            providers=["web", "docs"],
        )

        if not result.sources:
            return f"Could not verify claim: '{claim}'. No sources found."

        # Build verification report
        lines = [
            f"## Fact Verification: {claim}",
            "",
            f"**Sources consulted:** {len(result.sources)}",
            f"**Average trust score:** {sum(s.source.trust_score for s in result.sources) / len(result.sources):.2f}",
            "",
            "### Evidence",
            "",
        ]

        for i, rs in enumerate(result.sources, 1):
            lines.append(f"**[{i}]** {rs.source.title}")
            lines.append(f"    Source: {rs.source.source_provider} | Trust: {rs.source.trust_score:.2f}")
            lines.append(f"    URL: {rs.source.url}")
            lines.append(f"    Snippet: {rs.source.snippet[:200]}")
            lines.append("")

        return "\n".join(lines)

    async def get_documentation(
        self,
        user_id: str,
        workspace_id: str,
        framework: str,
        topic: str | None = None,
    ) -> str:
        """Fetch official documentation for a specific framework or library."""
        from app.knowledge_engine.engine import KnowledgeEngine

        engine = KnowledgeEngine()
        content = await engine.get_documentation(framework, topic)

        if not content:
            return f"No documentation found for '{framework}'. Try searching with web_search instead."

        return f"## {content.title}\n\n**Source:** {content.url}\n\n{content.text}"

    async def get_github_info(
        self,
        user_id: str,
        workspace_id: str,
        repo_name: str,
    ) -> str:
        """Fetch repository information, README, and latest release from GitHub."""
        from app.knowledge_engine.engine import KnowledgeEngine

        engine = KnowledgeEngine()

        # Search for the repo
        results = await engine.search(f"{repo_name}", max_results=3, provider="github")

        if not results:
            return f"No GitHub repository found matching '{repo_name}'."

        # Fetch the top result's content
        content = await engine.fetch(results[0].url)

        if content:
            return f"## {content.title}\n\n**URL:** {content.url}\n\n{content.text}"

        # Fallback to search result snippet
        lines = [f"## GitHub: {repo_name}", ""]
        for r in results:
            lines.append(f"### {r.title}")
            lines.append(f"**URL:** {r.url}")
            lines.append(f"{r.snippet}")
            lines.append("")
        return "\n".join(lines)

    async def summarize_knowledge(
        self,
        user_id: str,
        workspace_id: str,
        topic: str | None = None,
    ) -> str:
        """Summarize knowledge about a topic or the entire workspace using LLM."""
        from app.knowledge_engine.intelligence.summarizer import KnowledgeSummarizer

        summarizer = KnowledgeSummarizer()
        if topic:
            result = await summarizer.summarize_topic(workspace_id, topic)
        else:
            result = await summarizer.summarize_workspace(workspace_id)

        lines = [f"## Knowledge Summary" if not topic else f"## Summary: {topic}", ""]
        lines.append(result["summary"])
        lines.append("")

        if result.get("key_points"):
            lines.append("**Key Points:**")
            for point in result["key_points"]:
                lines.append(f"- {point}")
            lines.append("")

        sources_count = result.get("sources_count", result.get("total_items", 0))
        lines.append(f"*Based on {sources_count} knowledge sources.*")
        return "\n".join(lines)

    async def resolve_conflicts(
        self,
        user_id: str,
        workspace_id: str,
        topic: str,
    ) -> str:
        """Detect and resolve conflicting claims about a topic across knowledge sources."""
        from app.knowledge_engine.intelligence.conflict_resolver import ConflictResolver

        resolver = ConflictResolver()
        report = await resolver.detect_conflicts(workspace_id, topic)

        if report.conflicts_found == 0:
            return f"No conflicts found about '{topic}'. All sources agree or insufficient data."

        lines = [f"## Conflict Report: {topic}", ""]
        lines.append(f"**Conflicts found:** {report.conflicts_found}")
        lines.append(f"**Sources consulted:** {report.sources_consulted}")
        lines.append("")

        for i, group in enumerate(report.groups, 1):
            lines.append(f"### Conflict {i}: {group.topic}")
            lines.append(f"**Type:** {group.conflict_type} | **Confidence:** {group.confidence:.0%}")
            lines.append(f"**Resolution:** {group.resolution[:300]}")
            lines.append("")
            lines.append("**Disagreeing sources:**")
            for claim in group.claims:
                lines.append(f"- [{claim.source_provider}, trust={claim.trust_score:.2f}] {claim.content[:150]}")
            lines.append("")

        return "\n".join(lines)

    async def submit_feedback(
        self,
        user_id: str,
        workspace_id: str,
        item_id: str,
        rating: str,
        comment: str | None = None,
    ) -> str:
        """Submit feedback on a knowledge item's quality (helpful/not_helpful/outdated/incorrect)."""
        from app.knowledge_engine.intelligence.feedback import FeedbackTracker

        tracker = FeedbackTracker()
        await tracker.record_feedback(
            workspace_id=workspace_id,
            item_id=item_id,
            rating=rating,
            comment=comment,
        )
        return f"Feedback recorded: {rating} for item {item_id}"

    async def deduplicate_knowledge(
        self,
        user_id: str,
        workspace_id: str,
    ) -> str:
        """Find and remove near-duplicate knowledge items in the workspace."""
        from app.knowledge_engine.intelligence.deduplicator import SemanticDeduplicator

        dedup = SemanticDeduplicator()
        result = await dedup.deduplicate_workspace(workspace_id, dry_run=False)

        lines = [
            "## Deduplication Results",
            "",
            f"**Duplicate groups found:** {result['duplicate_groups']}",
            f"**Items removed:** {result['items_removed']}",
            f"**Items remaining:** {result['items_to_remove'] - result['items_removed']} pending",
        ]
        return "\n".join(lines)

    async def export_knowledge(
        self,
        user_id: str,
        workspace_id: str,
    ) -> str:
        """Export all knowledge for the workspace as a structured summary."""
        from app.knowledge_engine.intelligence.exporter import KnowledgeExporter

        exporter = KnowledgeExporter()
        result = await exporter.export_workspace(workspace_id, include_graph=True)

        stats = result["stats"]
        lines = [
            "## Knowledge Export",
            "",
            f"**Workspace:** {workspace_id}",
            f"**Items exported:** {result['item_count']}",
            f"**Providers:** {stats.get('providers', 0)}",
            f"**Average trust:** {stats.get('avg_trust', 0)}",
            f"**Total content:** {stats.get('total_content_kb', 0)} KB",
        ]

        if result.get("graph"):
            graph = result["graph"]
            lines.append(f"**Graph entities:** {len(graph.get('entities', []))}")
            lines.append(f"**Graph relationships:** {len(graph.get('relationships', []))}")

        lines.append("")
        lines.append(f"*Exported at: {result['exported_at']}*")
        return "\n".join(lines)

    async def knowledge_health(
        self,
        user_id: str,
        workspace_id: str,
    ) -> str:
        """Get a comprehensive health report for the workspace's knowledge base."""
        from app.knowledge_engine.intelligence.health_dashboard import KnowledgeHealthDashboard

        dashboard = KnowledgeHealthDashboard()
        result = await dashboard.get_health_report(workspace_id)

        health = result["overall_health"]
        stats = result["stats"]
        freshness = result["freshness"]

        lines = [
            "## Knowledge Health Report",
            "",
            f"### Overall: {health['grade'].upper()} ({health['score']}/100)",
            "",
            f"**Coverage:** {health['breakdown']['coverage']}/30 "
            f"({stats['total_items']} items)",
            f"**Freshness:** {health['breakdown']['freshness']}/30 "
            f"({freshness['this_week']} this week, {freshness['stale']} stale)",
            f"**Quality:** {health['breakdown']['quality']}/30",
            f"**Diversity:** {health['breakdown']['diversity']}/10 "
            f"({stats['providers']} providers)",
            "",
        ]

        if result.get("gaps"):
            lines.append("### Knowledge Gaps")
            for gap in result["gaps"][:5]:
                lines.append(f"- [{gap['severity']}] {gap['topic']}: {gap['description']}")
            lines.append("")

        if result.get("recommendations"):
            lines.append("### Recommendations")
            for rec in result["recommendations"]:
                lines.append(f"- {rec}")

        return "\n".join(lines)


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
            "description": "Search the web for general information, facts, documentation, "
            "or anything not available in your training data. Use this for research, "
            "how-to questions, library documentation, API references, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find information about.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5, max 10).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_news",
            "description": "Search for RECENT NEWS and current events. Use this when the user "
            "asks about latest news, recent developments, product launches, "
            "breaking news, or time-sensitive information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The news search query.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5).",
                    },
                    "timelimit": {
                        "type": "string",
                        "enum": ["d", "w", "m"],
                        "description": "Time limit: 'd' = past day, 'w' = past week, 'm' = past month. Default is 'd'.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search_instant",
            "description": "Get instant answers for calculations, conversions, definitions, "
            "unit conversions, quick facts, etc. Use for simple factual queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question to get an instant answer for.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and extract clean text content from a specific URL. "
            "Use this to read article content, documentation pages, blog posts, "
            "or any webpage. Returns clean readable text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to fetch content from (must include http:// or https://).",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browse_web",
            "description": "Browse a webpage and optionally answer a specific question about it. "
            "Use this when you need to read a specific page and extract relevant "
            "information to answer a user's question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to browse.",
                    },
                    "question": {
                        "type": "string",
                        "description": "What specific information to look for on the page (optional).",
                    },
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
    {
        "type": "function",
        "function": {
            "name": "research_topic",
            "description": "DEEP RESEARCH — searches multiple trusted sources (official docs, "
            "GitHub, research papers, news, package registries), ranks by trust "
            "and relevance, and returns verified context with citations. Use this "
            "for complex questions requiring thorough research, comparisons between "
            "technologies, best practices, architecture patterns, or any question "
            "where accuracy matters. This is the most powerful research tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The research question or topic to investigate thoroughly.",
                    },
                    "max_sources": {
                        "type": "integer",
                        "description": "Maximum number of sources to consult (default 5, max 10).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "verify_fact",
            "description": "Cross-check a specific claim or fact across multiple trusted sources "
            "to verify its accuracy. Returns evidence from sources with trust scores. "
            "Use this when you need to confirm a statement, check if something is "
            "still true, or validate a claim before presenting it to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string",
                        "description": "The specific claim or fact to verify.",
                    },
                },
                "required": ["claim"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_documentation",
            "description": "Fetch official documentation for a specific framework, library, "
            "or technology. Returns clean documentation content. Use this for "
            "how-to questions, API references, setup guides, or feature explanations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "framework": {
                        "type": "string",
                        "description": "The framework or technology (e.g., 'django', 'fastapi', 'react', 'docker', 'aws', 'postgresql').",
                    },
                    "topic": {
                        "type": "string",
                        "description": "Specific topic within the framework (e.g., 'authentication', 'middleware', 'hooks'). Optional.",
                    },
                },
                "required": ["framework"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_github_info",
            "description": "Fetch GitHub repository information, README, and latest release. "
            "Use this when the user asks about a specific open-source project, "
            "wants to see a repo's documentation, or needs release information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {
                        "type": "string",
                        "description": "The repository name (e.g., 'langchain', 'fastapi', 'facebook/react').",
                    },
                },
                "required": ["repo_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the PERSISTENT KNOWLEDGE BASE for previously stored research. "
            "ALWAYS call this FIRST before doing a fresh web search — the knowledge "
            "base may already have relevant information from previous research sessions, "
            "saving time and API calls. Use this for follow-up questions about topics "
            "already researched, or when checking if something was already investigated.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in the stored knowledge base.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "store_knowledge",
            "description": "Store a piece of knowledge into the persistent knowledge base. "
            "Use this when you find important information from browsing, manual research, "
            "or user-provided content that should be remembered for future sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The source URL of the knowledge.",
                    },
                    "title": {
                        "type": "string",
                        "description": "A descriptive title for this knowledge item.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The actual knowledge content to store.",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Where this knowledge came from (e.g., 'web', 'docs', 'manual').",
                    },
                    "summary": {
                        "type": "string",
                        "description": "A brief summary of the knowledge (optional).",
                    },
                },
                "required": ["url", "title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_knowledge_stats",
            "description": "Show statistics about the workspace's stored knowledge base — "
            "total items, providers used, trust scores, and date range.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_entity_graph",
            "description": "Find technologies and concepts related to a given entity via the "
            "knowledge graph. Shows how technologies connect (e.g., FastAPI depends on Python, "
            "integrates with PostgreSQL). Use when the user asks about relationships between "
            "technologies or wants to understand their tech stack connections.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "The entity to find relationships for (e.g., 'fastapi', 'django', 'postgresql').",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "How many hops to traverse in the graph (default 2, max 4).",
                    },
                },
                "required": ["entity_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_entities",
            "description": "Get the most mentioned technologies and concepts in the workspace's "
            "knowledge base. Shows what technologies are most frequently discussed or referenced.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["language", "framework", "database", "infrastructure", "tool", "concept"],
                        "description": "Filter by entity type (optional).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_proactive_learning",
            "description": "Run a PROACTIVE LEARNING cycle — automatically detect technologies "
            "used in the workspace, check for new releases and security advisories, and "
            "auto-index relevant updates into the knowledge base. Use this when the user "
            "wants to update their knowledge or check for new developments.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_knowledge",
            "description": "Generate an LLM-powered summary of knowledge about a specific topic "
            "or the entire workspace. Synthesizes multiple sources into key points. "
            "Use when the user wants a digest or overview of what's known.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to summarize (optional). If omitted, summarizes the entire workspace.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_conflicts",
            "description": "Detect and resolve contradictory claims across knowledge sources for a topic. "
            "Use when the user asks about conflicting information, wants to know which source to trust, "
            "or when you notice contradictory facts in your knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The topic to check for conflicts (e.g., 'is React better than Vue', 'Python version support').",
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_feedback",
            "description": "Submit feedback on a knowledge item's quality. Use this when the user "
            "says a response was helpful, unhelpful, outdated, or incorrect — the feedback "
            "adjusts the quality score of the referenced knowledge items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "The knowledge item ID to rate.",
                    },
                    "rating": {
                        "type": "string",
                        "enum": ["helpful", "not_helpful", "partially_helpful", "outdated", "incorrect"],
                        "description": "The feedback rating.",
                    },
                    "comment": {
                        "type": "string",
                        "description": "Optional comment about why.",
                    },
                },
                "required": ["item_id", "rating"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deduplicate_knowledge",
            "description": "Find and remove near-duplicate knowledge items in the workspace. "
            "Uses embedding similarity to detect same content published on different URLs. "
            "Use when the user wants to clean up the knowledge base.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_knowledge",
            "description": "Export all knowledge for the workspace as a structured summary with stats. "
            "Use when the user wants to see an overview of what's stored or needs a backup.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "knowledge_health",
            "description": "Get a comprehensive health report for the knowledge base — coverage, "
            "freshness, quality distribution, knowledge gaps, and actionable recommendations. "
            "Use when the user wants to understand the state of their knowledge base.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
