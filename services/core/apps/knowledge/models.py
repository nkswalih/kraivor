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
                fields=["workspace", "deleted_at"], name="idx_ks_workspace_active"
            ),
            # Search path: filter by workspace + name
            models.Index(fields=["workspace", "name"], name="idx_ks_workspace_name"),
        ]

    def __str__(self):
        return f"KnowledgeSpace({self.name!r}@{self.workspace.slug})"


class KnowledgeAsset(TimestampedModel):
    """
    File reference scoped to a knowledge space.

    Stores references to files uploaded by users — images, PDFs, and other
    binary assets placed on the canvas. Actual bytes live in S3/MinIO;
    this model tracks the metadata and access URL.

    file_type: Maps to MIME category — 'image', 'pdf', 'file', 'code'.
               The frontend uses this to decide how to render the asset.
    """

    knowledge_space = models.ForeignKey(
        KnowledgeSpace, on_delete=models.CASCADE, related_name="assets", db_index=True
    )
    file_name = models.CharField(
        max_length=512, help_text="Original file name including extension."
    )
    file_size = models.BigIntegerField(help_text="File size in bytes.")
    file_type = models.CharField(
        max_length=32,
        choices=[
            ("image", "Image"),
            ("pdf", "PDF"),
            ("file", "File"),
            ("code", "Code"),
        ],
        default="file",
    )
    mime_type = models.CharField(
        max_length=127, help_text="MIME type (e.g. image/png, application/pdf)."
    )
    storage_key = models.CharField(
        max_length=1024,
        unique=True,
        help_text="S3/MinIO object key used to retrieve the file.",
    )
    url = models.URLField(
        max_length=2048,
        null=True,
        blank=True,
        help_text="Pre-signed or public URL for direct access.",
    )
    uploaded_by = models.UUIDField(
        help_text="identity.users.id of the user who uploaded this file."
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary metadata (e.g. image dimensions, page count).",
    )

    class Meta:
        db_table = "knowledge_assets"
        indexes = [
            models.Index(
                fields=["knowledge_space", "file_type"], name="idx_ka_space_type"
            ),
            models.Index(fields=["uploaded_by"], name="idx_ka_uploaded_by"),
        ]
        verbose_name = "Knowledge Asset"
        verbose_name_plural = "Knowledge Assets"

    def __str__(self):
        return f"KnowledgeAsset({self.file_name!r})"


class KnowledgeSpaceVersion(TimestampedModel):
    """
    Immutable canvas snapshot for undo/redo history.

    Each time the frontend autosaves the canvas, the service layer MAY
    create a new version if the canvas_data has changed since the last
    version. The frontend can request a specific version by number to
    restore canvas state.

    version_number: Monotonically increasing within a knowledge space.
    canvas_snapshot: Deep copy of canvas_data at the point of save.
    created_by: User who triggered the save.
    """

    knowledge_space = models.ForeignKey(
        KnowledgeSpace, on_delete=models.CASCADE, related_name="versions", db_index=True
    )
    version_number = models.PositiveIntegerField(
        help_text="Incremental version number within this knowledge space."
    )
    canvas_snapshot = models.JSONField(
        help_text="Deep copy of canvas_data at this version."
    )
    created_by = models.UUIDField(
        help_text="identity.users.id of the user who triggered this save."
    )
    description = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional human-readable label (e.g. 'Added architecture diagram').",
    )

    class Meta:
        db_table = "knowledge_space_versions"
        constraints = [
            models.UniqueConstraint(
                fields=["knowledge_space", "version_number"], name="uq_ksv_version"
            )
        ]
        indexes = [
            models.Index(
                fields=["knowledge_space", "-version_number"],
                name="idx_ksv_version_desc",
            )
        ]
        ordering = ["-version_number"]
        verbose_name = "Knowledge Space Version"
        verbose_name_plural = "Knowledge Space Versions"

    def __str__(self):
        return f"KnowledgeSpaceVersion({self.knowledge_space.name!r} v{self.version_number})"
