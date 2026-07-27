"""Knowledge Graph — entity extraction, relationship mapping, and graph queries.

Uses PostgreSQL graph tables (no external graph DB needed) to track:
- Entities extracted from knowledge (technologies, frameworks, concepts)
- Relationships between entities (depends_on, related_to, part_of, etc.)
- Connections between knowledge items via shared entities

This enables "find related knowledge" and "trace concept lineage" queries.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import text

from app.infrastructure.db.database import async_session_factory

logger = logging.getLogger(__name__)

# ── Entity Extraction ────────────────────────────────────────────────────────

# Curated technology entity patterns
TECH_ENTITIES = {
    # Languages
    "python": "language", "javascript": "language", "typescript": "language",
    "rust": "language", "go": "language", "java": "language", "c++": "language",
    "ruby": "language", "php": "language", "swift": "language", "kotlin": "language",
    # Frameworks
    "django": "framework", "fastapi": "framework", "flask": "framework",
    "react": "framework", "vue": "framework", "angular": "framework",
    "nextjs": "framework", "nuxt": "framework", "svelte": "framework",
    "spring": "framework", "rails": "framework", "express": "framework",
    "fiber": "framework", "gin": "framework", "echo": "framework",
    # Databases
    "postgresql": "database", "postgres": "database", "mysql": "database",
    "mongodb": "database", "redis": "database", "sqlite": "database",
    "elasticsearch": "database", "cassandra": "database", "dynamodb": "database",
    "neo4j": "database", "influxdb": "database", "clickhouse": "database",
    # Infrastructure
    "docker": "infrastructure", "kubernetes": "infrastructure", "k8s": "infrastructure",
    "aws": "infrastructure", "gcp": "infrastructure", "azure": "infrastructure",
    "terraform": "infrastructure", "ansible": "infrastructure", "helm": "infrastructure",
    "nginx": "infrastructure", "apache": "infrastructure", "traefik": "infrastructure",
    # Tools
    "git": "tool", "github": "tool", "gitlab": "tool", "jenkins": "tool",
    "ci/cd": "tool", "github actions": "tool", "circleci": "tool",
    "prometheus": "tool", "grafana": "tool", "datadog": "tool",
    # Concepts
    "rest api": "concept", "graphql": "concept", "grpc": "concept",
    "microservices": "concept", "monolith": "concept", "serverless": "concept",
    "kafka": "concept", "rabbitmq": "concept", "celery": "concept",
    "jwt": "concept", "oauth": "concept", "oauth2": "concept",
    "cors": "concept", "csrf": "concept", "ssl": "concept", "tls": "concept",
    "devops": "concept", "mlops": "concept",
    "agile": "concept", "scrum": "concept", "kanban": "concept",
}

# Relationship patterns between entities
RELATIONSHIP_PATTERNS = [
    (r"(.+?)\s+(?:uses?|built with|powered by|depends on)\s+(.+)", "depends_on"),
    (r"(.+?)\s+(?:alternatives? to|compared with|versus|vs\.?)\s+(.+)", "related_to"),
    (r"(.+?)\s+(?:integrates? with|connects? to|works? with)\s+(.+)", "integrates_with"),
    (r"(.+?)\s+(?:part of|component of|module of)\s+(.+)", "part_of"),
    (r"(.+?)\s+(?:replaces?|successor to|supersedes?)\s+(.+)", "replaces"),
    (r"(.+?)\s+(?:extends?|enhances?|improves?)\s+(.+)", "extends"),
]


def extract_entities(text_content: str) -> list[dict]:
    """Extract technology entities from text content."""
    text_lower = text_content.lower()
    found = []

    for entity, etype in TECH_ENTITIES.items():
        if entity in text_lower:
            found.append({"name": entity, "type": etype})

    # Deduplicate
    seen = set()
    unique = []
    for e in found:
        if e["name"] not in seen:
            seen.add(e["name"])
            unique.append(e)

    return unique


def extract_relationships(text_content: str) -> list[dict]:
    """Extract entity relationships from text content."""
    relationships = []
    text_lower = text_content.lower()

    for pattern, rel_type in RELATIONSHIP_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            source = match.group(1).strip()
            target = match.group(2).strip()
            # Only keep if both are known entities
            if source in TECH_ENTITIES and target in TECH_ENTITIES and source != target:
                relationships.append({
                    "source": source,
                    "target": target,
                    "type": rel_type,
                })

    return relationships


# ── Graph Store ──────────────────────────────────────────────────────────────


class KnowledgeGraph:
    """Manages the knowledge graph — entities, relationships, and connections."""

    async def ensure_tables(self):
        """Create graph tables if they don't exist."""
        async with async_session_factory() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS ai.knowledge_entities (
                    id VARCHAR PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    entity_type VARCHAR(50) NOT NULL,
                    mention_count INTEGER DEFAULT 1,
                    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    metadata JSONB,
                    UNIQUE(workspace_id, name)
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_ke_workspace
                ON ai.knowledge_entities(workspace_id)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_ke_type
                ON ai.knowledge_entities(workspace_id, entity_type)
            """))

            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS ai.knowledge_relationships (
                    id VARCHAR PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    source_entity VARCHAR(255) NOT NULL,
                    target_entity VARCHAR(255) NOT NULL,
                    relationship_type VARCHAR(50) NOT NULL,
                    weight FLOAT DEFAULT 1.0,
                    evidence_count INTEGER DEFAULT 1,
                    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(workspace_id, source_entity, target_entity, relationship_type)
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_kr_workspace
                ON ai.knowledge_relationships(workspace_id)
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_kr_source
                ON ai.knowledge_relationships(workspace_id, source_entity)
            """))

            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS ai.knowledge_connections (
                    id VARCHAR PRIMARY KEY,
                    workspace_id VARCHAR NOT NULL,
                    item_id VARCHAR NOT NULL,
                    connected_item_id VARCHAR NOT NULL,
                    shared_entities TEXT[],
                    connection_strength FLOAT DEFAULT 0.0,
                    UNIQUE(workspace_id, item_id, connected_item_id)
                )
            """))
            await session.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_kc_workspace_item
                ON ai.knowledge_connections(workspace_id, item_id)
            """))

            await session.commit()

    async def index_entities(
        self,
        workspace_id: str,
        item_id: str,
        text_content: str,
    ):
        """Extract and index entities from a knowledge item's content."""
        entities = extract_entities(text_content)
        if not entities:
            return

        async with async_session_factory() as session:
            for entity in entities:
                name = entity["name"]
                etype = entity["type"]

                await session.execute(text("""
                    INSERT INTO ai.knowledge_entities
                        (id, workspace_id, name, entity_type, mention_count, first_seen, last_seen)
                    VALUES
                        (MD5(:workspace_id || :name), :workspace_id, :name, :etype, 1, NOW(), NOW())
                    ON CONFLICT (workspace_id, name) DO UPDATE SET
                        mention_count = ai.knowledge_entities.mention_count + 1,
                        last_seen = NOW()
                """), {
                    "workspace_id": workspace_id,
                    "name": name,
                    "etype": etype,
                })

            await session.commit()

        logger.debug("Indexed %d entities for item %s", len(entities), item_id)
        return entities

    async def index_relationships(
        self,
        workspace_id: str,
        text_content: str,
    ):
        """Extract and index relationships from text content."""
        relationships = extract_relationships(text_content)
        if not relationships:
            return

        import hashlib

        async with async_session_factory() as session:
            for rel in relationships:
                rel_id = hashlib.sha256(
                    f"{workspace_id}:{rel['source']}:{rel['target']}:{rel['type']}".encode()
                ).hexdigest()[:24]

                await session.execute(text("""
                    INSERT INTO ai.knowledge_relationships
                        (id, workspace_id, source_entity, target_entity, relationship_type,
                         weight, evidence_count, first_seen, last_seen)
                    VALUES
                        (:id, :ws, :src, :tgt, :rtype, 1.0, 1, NOW(), NOW())
                    ON CONFLICT (workspace_id, source_entity, target_entity, relationship_type) DO UPDATE SET
                        weight = LEAST(ai.knowledge_relationships.weight + 0.1, 10.0),
                        evidence_count = ai.knowledge_relationships.evidence_count + 1,
                        last_seen = NOW()
                """), {
                    "id": rel_id,
                    "ws": workspace_id,
                    "src": rel["source"],
                    "tgt": rel["target"],
                    "rtype": rel["type"],
                })

            await session.commit()

        return relationships

    async def find_related(
        self,
        workspace_id: str,
        entity_name: str,
        max_depth: int = 2,
    ) -> list[dict]:
        """Find entities related to a given entity via the graph."""
        async with async_session_factory() as session:
            result = await session.execute(text("""
                WITH RECURSIVE graph_walk AS (
                    SELECT
                        target_entity,
                        relationship_type,
                        weight,
                        1 AS depth
                    FROM ai.knowledge_relationships
                    WHERE workspace_id = :ws
                      AND source_entity = LOWER(:entity)

                    UNION ALL

                    SELECT
                        kr.target_entity,
                        kr.relationship_type,
                        kr.weight * gw.weight AS weight,
                        gw.depth + 1
                    FROM ai.knowledge_relationships kr
                    JOIN graph_walk gw ON kr.source_entity = gw.target_entity
                    WHERE kr.workspace_id = :ws
                      AND gw.depth < :max_depth
                )
                SELECT
                    target_entity,
                    relationship_type,
                    SUM(weight) AS total_weight,
                    COUNT(*) AS path_count
                FROM graph_walk
                GROUP BY target_entity, relationship_type
                ORDER BY total_weight DESC
                LIMIT 20
            """), {"ws": workspace_id, "entity": entity_name, "max_depth": max_depth})
            rows = result.fetchall()

        return [
            {
                "entity": row.target_entity,
                "relationship": row.relationship_type,
                "weight": round(float(row.total_weight), 2),
                "path_count": row.path_count,
            }
            for row in rows
        ]

    async def get_entity_context(
        self,
        workspace_id: str,
        entities: list[str],
    ) -> str:
        """Build a graph context string for entities — their relationships and connections."""
        if not entities:
            return ""

        lines = ["## Entity Relationships"]
        for entity in entities[:5]:
            related = await self.find_related(workspace_id, entity)
            if related:
                lines.append(f"\n**{entity}:**")
                for r in related[:5]:
                    lines.append(f"  - {r['relationship']} {r['entity']} (strength: {r['weight']})")

        return "\n".join(lines) if len(lines) > 1 else ""

    async def get_workspace_entities(
        self,
        workspace_id: str,
        entity_type: str | None = None,
        top_n: int = 20,
    ) -> list[dict]:
        """Get the most mentioned entities in a workspace."""
        async with async_session_factory() as session:
            if entity_type:
                result = await session.execute(text("""
                    SELECT name, entity_type, mention_count, first_seen, last_seen
                    FROM ai.knowledge_entities
                    WHERE workspace_id = :ws AND entity_type = :etype
                    ORDER BY mention_count DESC
                    LIMIT :top_n
                """), {"ws": workspace_id, "etype": entity_type, "top_n": top_n})
            else:
                result = await session.execute(text("""
                    SELECT name, entity_type, mention_count, first_seen, last_seen
                    FROM ai.knowledge_entities
                    WHERE workspace_id = :ws
                    ORDER BY mention_count DESC
                    LIMIT :top_n
                """), {"ws": workspace_id, "top_n": top_n})
            rows = result.fetchall()

        return [
            {
                "name": row.name,
                "type": row.entity_type,
                "mentions": row.mention_count,
                "first_seen": row.first_seen.isoformat() if row.first_seen else None,
                "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            }
            for row in rows
        ]

    async def get_entity_stats(self, workspace_id: str) -> dict:
        """Get graph statistics for a workspace."""
        async with async_session_factory() as session:
            entities = await session.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT entity_type) as types
                FROM ai.knowledge_entities
                WHERE workspace_id = :ws
            """), {"ws": workspace_id})
            e_row = entities.fetchone()

            rels = await session.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT relationship_type) as rel_types
                FROM ai.knowledge_relationships
                WHERE workspace_id = :ws
            """), {"ws": workspace_id})
            r_row = rels.fetchone()

        return {
            "entities": e_row.total or 0,
            "entity_types": e_row.types or 0,
            "relationships": r_row.total or 0,
            "relationship_types": r_row.rel_types or 0,
        }
