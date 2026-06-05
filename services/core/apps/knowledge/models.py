"""
Knowledge Space models — KRV-022 (Knowledge Workspace / Infinite Canvas).

A KnowledgeSpace is a workspace-scoped infinite canvas for software engineering
teams. Each space is identified by a name (e.g. "Authentication System",
"Payment Service") and stores its entire canvas state as a JSONB blob.

The frontend is fully responsible for rendering the canvas. The backend stores
and retrieves the canvas_data atomically — it treats the blob as opaque.

Canvas items the frontend may place on the canvas:
  Text, Markdown, Code Blocks, Images, PDFs, Files, Flow Charts,
  Architecture Diagrams, Sticky Notes, Repository References,
  Task References, AI Responses.

Design rules (system design §6):
  - All PKs are UUIDs (inherited from TimestampedModel)
  - Soft deletes everywhere (deleted_at TIMESTAMPTZ via TimestampedModel)
  - created_at / updated_at on every table (via TimestampedModel)
  - No cross-service DB FKs — user references are plain UUIDs
"""

from django.db import models

from apps.workspaces.models import TimestampedModel, Workspace


class KnowledgeSpace(TimestampedModel):
    """
    Infinite canvas scoped to a workspace.

    canvas_data stores the complete frontend canvas state as a JSONB blob.
    The backend treats this field as opaque: it stores whatever the frontend
    sends and returns it verbatim. Shape versioning and schema migrations are
    the frontend's responsibility.

    created_by / updated_by:
      Denormalized UUID references to identity.users — no DB FK to avoid
      cross-service coupling (system design §1). Same pattern as
      connected_by_id on Repository and invited_by_id on WorkspaceMember.
      updated_by is None until the first update after creation.
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="knowledge_spaces",
        db_index=True,
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name for this canvas (e.g. 'Authentication System').",
    )
    description = models.TextField(
        null=True,
        blank=True,
        max_length=1000,
        help_text="Optional description of the canvas purpose and scope.",
    )
    canvas_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Full infinite canvas state as an opaque JSONB blob. "
            "The backend stores and retrieves this field atomically; "
            "the frontend owns the shape and rendering."
        ),
    )
    created_by = models.UUIDField(
        db_index=True,
        help_text="identity.users.id of the user who created this canvas.",
    )
    updated_by = models.UUIDField(
        null=True,
        blank=True,
        help_text=(
            "identity.users.id of the user who last updated this canvas. "
            "Null until the first update after creation."
        ),
    )

    class Meta:
        db_table = "knowledge_spaces"
        indexes = [
            # Hot path: list active spaces for a workspace
            models.Index(
                fields=["workspace", "deleted_at"],
                name="idx_ks_workspace_active",
            ),
            # Search path: filter by workspace + name
            models.Index(
                fields=["workspace", "name"],
                name="idx_ks_workspace_name",
            ),
        ]

    def __str__(self):
        return f"KnowledgeSpace({self.name!r}@{self.workspace.slug})"