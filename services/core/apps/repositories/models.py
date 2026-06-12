"""
Repository models — KRV-021 (Repository Metadata Management).

Repository stores GitHub repository metadata linked to a workspace.
This metadata is consumed by the Analysis Service and AI Service.

Design rules (system design §6):
  - All PKs are UUIDs (inherited from TimestampedModel)
  - Soft deletes everywhere (deleted_at TIMESTAMPTZ via TimestampedModel)
  - created_at / updated_at on every table (via TimestampedModel)
  - No cross-service DB FKs — user references are plain UUIDs
"""

from django.db import models

from apps.workspaces.models import TimestampedModel, Workspace

from .github_app.models import (
    GitHubAppInstallation,
    GitHubAppInstallationRepo,  # noqa: F401 — needed for migration discovery
)


class Repository(TimestampedModel):
    """
    GitHub repository connected to a workspace.

    Uniqueness:
      A repository is identified within a workspace by its stable GitHub
      repository ID (github_id). The github_repo ("owner/name") string can
      change when a repo is renamed or transferred; github_id never changes.
      unique_together on (workspace, github_id) enforces one-connection-per-repo
      per workspace while allowing the same repo to appear in multiple workspaces.

    Soft delete:
      Disconnecting a repo sets deleted_at via TimestampedModel.delete().
      Reconnecting a previously disconnected repo restores the row (same pattern
      as WorkspaceMember re-invitation) so that historical analysis data is
      preserved against the same primary key.

    connected_by_id:
      Denormalized audit field — identity service UUID of the user who connected
      the repository. Consistent with invited_by_id on WorkspaceMember.
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="repositories",
        db_index=True,
    )
    github_repo = models.CharField(
        max_length=255,
        db_index=True,
        help_text="GitHub repository in 'owner/repo' format (e.g. 'acme/api'). "
        "Updated automatically when metadata is refreshed.",
    )
    github_id = models.BigIntegerField(
        db_index=True,
        help_text="Stable GitHub repository ID. Does not change on rename or transfer.",
    )
    default_branch = models.CharField(
        max_length=255,
        default="main",
        help_text="Default branch name as reported by GitHub.",
    )
    language = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Primary programming language as reported by GitHub. Null if not detected.",
    )
    description = models.TextField(
        null=True,
        blank=True,
        max_length=500,
        help_text="Repository description from GitHub. Truncated at 500 characters.",
    )
    is_private = models.BooleanField(
        default=False,
        help_text="Whether the GitHub repository is private.",
    )
    last_analyzed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Timestamp of the last completed analysis run by the Analysis Service.",
    )
    last_analysis_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Aggregate score (0.00–100.00) from the last analysis run.",
    )
    indexed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether the repository has been indexed for AI/RAG search by the AI Service.",
    )
    connected_by_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="identity.users.id of the user who connected the repository. Audit trail.",
    )
    installation = models.ForeignKey(
        GitHubAppInstallation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="repositories",
        help_text="GitHub App installation used to access this repository. "
        "Null for repos connected via legacy OAuth.",
    )

    class Meta:
        db_table = "repositories"
        # Prevents connecting the same GitHub repo twice to one workspace.
        # Soft-deleted rows are also covered — the service layer handles resurrection
        # rather than creating a second row.
        unique_together = [("workspace", "github_id")]
        indexes = [
            # List active repos for a workspace (hot path)
            models.Index(
                fields=["workspace", "deleted_at"],
                name="idx_repos_workspace_active",
            ),
            # Look up by owner/name string (duplicate-connect check)
            models.Index(
                fields=["workspace", "github_repo"],
                name="idx_workspace_github_repo",
            ),
        ]

    def __str__(self):
        return f"Repository({self.github_repo}@{self.workspace.slug})"
