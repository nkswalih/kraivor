from django.db import models

from apps.workspaces.models import TimestampedModel, Workspace


class GitHubAppInstallation(TimestampedModel):
    """
    Tracks a GitHub App installation linked to a workspace.

    Each installation represents a GitHub account (user or organization)
    that has installed the GitHub App and granted access to specific repos.

    The installation token is never stored in the DB — it is fetched on
    demand via JWT-authenticated API calls and cached in memory for its
    lifetime (1 hour).
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="github_app_installations",
        db_index=True,
        help_text="Workspace that owns this installation.",
    )
    installation_id = models.BigIntegerField(
        unique=True,
        db_index=True,
        help_text="GitHub App installation ID (assigned by GitHub).",
    )
    github_account_id = models.BigIntegerField(
        help_text="GitHub account (user or org) ID that installed the app.",
    )
    github_account_login = models.CharField(
        max_length=255,
        help_text="GitHub account login (e.g. 'acme-corp' or 'john').",
    )
    github_account_type = models.CharField(
        max_length=20,
        help_text="'User' or 'Organization'.",
    )
    installed_by_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="identity.users.id of the user who initiated the installation.",
    )
    repositories_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the accessible repo list was synced from GitHub.",
    )

    class Meta:
        db_table = "github_app_installations"
        indexes = [
            models.Index(
                fields=["workspace", "deleted_at"],
                name="idx_gh_install_ws_active",
            ),
        ]

    def __str__(self):
        return (
            f"GitHubAppInstallation({self.github_account_login}, "
            f"id={self.installation_id}, workspace={self.workspace_id})"
        )


class GitHubAppInstallationRepo(TimestampedModel):
    """
    Repositories accessible through a GitHub App installation.

    Synced from GitHub when the installation is created or manually refreshed.
    Used by the repo picker to list available repos without calling GitHub API
    on every request.

    Soft-delete is NOT used here — rows are bulk-replaced on each sync.
    """

    installation = models.ForeignKey(
        GitHubAppInstallation,
        on_delete=models.CASCADE,
        related_name="repos",
        db_index=True,
    )
    github_id = models.BigIntegerField(
        db_index=True,
        help_text="Stable GitHub repository ID.",
    )
    github_repo = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Full repo name in 'owner/repo' format.",
    )
    default_branch = models.CharField(
        max_length=255,
        default="main",
    )
    is_private = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True, max_length=500)
    language = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "github_app_installation_repos"
        unique_together = [("installation", "github_id")]
        indexes = [
            models.Index(
                fields=["installation", "github_repo"],
                name="idx_install_repo_name",
            ),
        ]

    def __str__(self):
        return f"InstallRepo({self.github_repo}, install={self.installation_id})"
