"""Kraivor project documentation seed data.

Public-facing project info only. No internal architecture, system design,
or technical implementation details — those stay in code.

Usage:
    from app.knowledge_engine.seed.kraivor_docs import KRAIVOR_DOCS
    for doc in KRAIVOR_DOCS:
        await indexer.index_knowledge(workspace_id=ws_id, **doc)
"""

KRAIVOR_DOCS = [
    {
        "source_url": "kraivor://project/overview",
        "source_provider": "project_docs",
        "title": "Kraivor — What Is It?",
        "content": """Kraivor is a unified developer intelligence platform — the operating system for developer intelligence.

        Tagline: "One workspace. Infinite codebase memory."

        Kraivor combines three pillars into a single authenticated workspace:

        1. Repository Analyzer — Deep structural analysis of any codebase. Generates Production Readiness Scores with prioritized remediation reports across security, performance, maintainability, and architecture.

        2. Agentic AI System — A multi-agent AI workspace where specialized agents collaborate on your codebase with full context awareness. The AI can search the web, retrieve stored knowledge, and use tools to answer complex engineering questions.

        3. Developer Productivity Platform — Unified workspace for notes, projects, tasks, knowledge spaces, and real-time collaboration — all enriched with live AI context.

        Vision: "Kraivor isn't building another dev tool. It's building the unified operating system for developer intelligence — the layer that sits between your code and your team, remembering everything so nobody has to."

        Mission: Engineering resilience, democratized.

        The platform targets three tiers:
        - Kraivor Solo — Individual developers
        - Kraivor Team — Engineering teams
        - Kraivor Enterprise — Organizations""",
        "trust_score": 0.95,
        "metadata": {"category": "project_overview", "priority": "high"},
    },
    {
        "source_url": "kraivor://project/creator",
        "source_provider": "project_docs",
        "title": "Kraivor — Creator & Project Context",
        "content": """Kraivor was created by Mohammed Swalih N K (nkswalih on GitHub).

        The project is an open-source developer intelligence platform focused on:
        - Repository analysis and code quality
        - AI-powered engineering insights
        - Developer productivity
        - Scalable software architecture

        Kraivor is built with the belief that the next generation of engineering orgs won't be defined by how many tools they've integrated — they'll be defined by how little context they lose.

        GitHub: https://github.com/nkswalih/kraivor
        License: MIT""",
        "trust_score": 0.9,
        "metadata": {"category": "project_context", "priority": "medium"},
    },
]
