"""Bundle Manager — export and import knowledge bundles.

Knowledge bundles are portable, versioned packages of knowledge items
that can be shared between workspaces or imported from templates.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeBundle:
    """A portable knowledge bundle."""
    bundle_id: str
    name: str
    description: str
    version: str
    author: str | None = None
    created_at: float = 0.0
    items: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    item_count: int = 0
    checksum: str = ""


@dataclass
class ImportResult:
    """Result from importing a bundle."""
    success: bool
    bundle_id: str
    items_imported: int
    items_skipped: int
    errors: list[str] = field(default_factory=list)


class BundleManager:
    """Manages knowledge bundle export and import."""

    BUNDLE_VERSION = "1.0"

    async def export_bundle(
        self,
        workspace_id: str,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        include_embeddings: bool = False,
    ) -> KnowledgeBundle:
        """Export workspace knowledge as a portable bundle."""
        from app.knowledge_engine.store.knowledge_store import KnowledgeStore

        store = KnowledgeStore()
        items = await store.list_items(workspace_id, limit=10000)

        # Convert items to bundle format
        bundle_items = []
        for item in items:
            bundle_item = {
                "source_url": item["source_url"],
                "source_provider": item["source_provider"],
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "trust_score": item.get("source_trust_score", 0.5),
                "summary": item.get("summary"),
                "source_type": item.get("source_type"),
                "language": item.get("language"),
                "metadata": item.get("metadata"),
            }
            if include_embeddings and item.get("embedding"):
                bundle_item["embedding"] = item["embedding"]
            bundle_items.append(bundle_item)

        # Generate checksum
        content_str = json.dumps(bundle_items, sort_keys=True, default=str)
        checksum = hashlib.sha256(content_str.encode()).hexdigest()[:16]

        bundle = KnowledgeBundle(
            bundle_id=checksum,
            name=name or f"Knowledge Bundle - {workspace_id}",
            description=description or f"Exported from workspace {workspace_id}",
            version=self.BUNDLE_VERSION,
            created_at=time.time(),
            items=bundle_items,
            metadata={
                "source_workspace": workspace_id,
                "export_format": "kraivor-bundle-v1",
                "item_count": len(bundle_items),
            },
            tags=tags or [],
            item_count=len(bundle_items),
            checksum=checksum,
        )

        logger.info(
            "Exported bundle %s: %d items from workspace %s",
            bundle.bundle_id, bundle.item_count, workspace_id,
        )
        return bundle

    async def import_bundle(
        self,
        workspace_id: str,
        bundle: KnowledgeBundle,
        skip_existing: bool = True,
    ) -> ImportResult:
        """Import a knowledge bundle into a workspace."""
        from app.knowledge_engine.store.knowledge_indexer import KnowledgeIndexer

        indexer = KnowledgeIndexer()
        imported = 0
        skipped = 0
        errors = []

        for item in bundle.items:
            try:
                source_url = item.get("source_url", "")
                source_provider = item.get("source_provider", "bundle")
                title = item.get("title", "")
                content = item.get("content", "")

                if not content:
                    skipped += 1
                    continue

                await indexer.index_knowledge(
                    workspace_id=workspace_id,
                    source_url=source_url,
                    source_provider=source_provider,
                    title=title,
                    content=content,
                    trust_score=item.get("trust_score", 0.5),
                    summary=item.get("summary"),
                    metadata=item.get("metadata"),
                    source_type=item.get("source_type"),
                    language=item.get("language"),
                )
                imported += 1
            except Exception as e:
                errors.append(f"Failed to import item {item.get('source_url', '?')}: {e}")
                skipped += 1

        result = ImportResult(
            success=len(errors) == 0,
            bundle_id=bundle.bundle_id,
            items_imported=imported,
            items_skipped=skipped,
            errors=errors,
        )

        logger.info(
            "Imported bundle %s into %s: %d imported, %d skipped",
            bundle.bundle_id, workspace_id, imported, skipped,
        )
        return result

    def serialize_bundle(self, bundle: KnowledgeBundle) -> str:
        """Serialize a bundle to JSON string."""
        return json.dumps({
            "bundle_id": bundle.bundle_id,
            "name": bundle.name,
            "description": bundle.description,
            "version": bundle.version,
            "author": bundle.author,
            "created_at": bundle.created_at,
            "items": bundle.items,
            "metadata": bundle.metadata,
            "tags": bundle.tags,
            "item_count": bundle.item_count,
            "checksum": bundle.checksum,
        }, indent=2, default=str)

    def deserialize_bundle(self, data: str) -> KnowledgeBundle:
        """Deserialize a bundle from JSON string."""
        parsed = json.loads(data)
        return KnowledgeBundle(
            bundle_id=parsed["bundle_id"],
            name=parsed["name"],
            description=parsed["description"],
            version=parsed["version"],
            author=parsed.get("author"),
            created_at=parsed.get("created_at", 0),
            items=parsed.get("items", []),
            metadata=parsed.get("metadata", {}),
            tags=parsed.get("tags", []),
            item_count=parsed.get("item_count", 0),
            checksum=parsed.get("checksum", ""),
        )
