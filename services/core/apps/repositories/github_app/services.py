"""
GitHub App installation service — manages the installation lifecycle.

Handles:
  - State token generation and validation (via Redis)
  - Installation creation and repo syncing from GitHub API
  - Repo list querying for the frontend picker
  - Finding the right installation to access a specific repo
"""

import json
import logging
import secrets
import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.workspaces.models import Workspace
from core.infrastructure.redis import get_redis

from .client import GitHubAppClient, GitHubAppError, _token_cache
from .models import GitHubAppInstallation, GitHubAppInstallationRepo

logger = logging.getLogger(__name__)


# ─── State Token Manager (Redis-backed) ────────────────────────────────────────


class InstallationStateManager:
    """
    Manages OAuth-like state tokens for GitHub App installation flow.

    The state parameter prevents CSRF attacks and encodes the workspace
    context so the callback can reconstruct it without exposing internal
    IDs in the URL.

    State tokens are stored in Redis with a 10-minute TTL.
    """

    STATE_TTL_SECONDS = 600  # 10 minutes
    REDIS_PREFIX = "gh_install_state:"

    def _get_redis(self):
        try:

            return get_redis()
        except ImportError:
            logger.warning(
                "install_state.redis_unavailable",
                extra={"reason": "redis module not found"},
            )
            return None

    def create_state(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> str:
        """
        Generate a cryptographically random state token and store it in Redis.

        Returns the raw state string to be passed as a query parameter.
        """
        state = secrets.token_urlsafe(32)
        payload = json.dumps(
            {"workspace_id": str(workspace_id), "user_id": str(user_id)}
        )

        redis_client = self._get_redis()
        if redis_client:
            redis_client.setex(
                f"{self.REDIS_PREFIX}{state}", self.STATE_TTL_SECONDS, payload
            )
        else:
            logger.warning(
                "install_state.no_redis",
                extra={"message": "Redis unavailable; state management disabled."},
            )

        return state

    def consume_state(self, state: str) -> dict[str, str] | None:
        """
        Validate and consume a state token.

        Returns the decoded payload dict (workspace_id, user_id) if valid,
        or None if the state is invalid or expired. The token is deleted
        after consumption (one-time use).
        """
        redis_client = self._get_redis()
        if not redis_client:
            return None

        key = f"{self.REDIS_PREFIX}{state}"
        payload = redis_client.get(key)
        if not payload:
            return None

        redis_client.delete(key)

        try:
            return json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            return None


# ─── Installation Service ──────────────────────────────────────────────────────


class GitHubAppInstallationService:
    """
    Manages the lifecycle of GitHub App installations.

    Instantiate per-request. No shared mutable state.
    """

    def __init__(
        self,
        client: GitHubAppClient | None = None,
        state_manager: InstallationStateManager | None = None,
    ):
        self._client = client or GitHubAppClient()
        self._state_manager = state_manager or InstallationStateManager()

    # ── Initiate Installation ─────────────────────────────────────────────────

    def initiate_installation(self, workspace: Workspace, actor_id: uuid.UUID) -> str:
        """
        Generate a state token and return the GitHub App installation URL.

        The frontend should redirect the user to this URL.
        """
        state = self._state_manager.create_state(
            workspace_id=workspace.id, user_id=actor_id
        )
        return self._client.get_installation_url(state=state)

    def get_configure_url(
        self, installation_id: int, workspace: Workspace, actor_id: uuid.UUID
    ) -> str:
        """
        Return the GitHub App reconfigure URL for an existing installation.

        This allows users to change which repositories the app can access
        without reinstalling. GitHub redirects back to the same callback URL.
        """
        try:
            GitHubAppInstallation.objects.get(
                installation_id=installation_id,
                workspace=workspace,
                deleted_at__isnull=True,
            )
        except GitHubAppInstallation.DoesNotExist as exc:
            raise GitHubAppError(
                f"Installation {installation_id} not found in this workspace."
            ) from exc

        state = self._state_manager.create_state(
            workspace_id=workspace.id, user_id=actor_id
        )
        return (
            f"https://github.com/apps/{self._client._slug}"
            f"/installations/{installation_id}"
            f"?state={state}"
        )

    # ── Complete Installation (Callback Handler) ──────────────────────────────

    @transaction.atomic
    def complete_installation(
        self, state: str, installation_id: int, setup_action: str
    ) -> dict[str, Any]:
        """
        Process the GitHub App installation callback.

        1. Validate and consume the state token
        2. Fetch installation metadata from GitHub API
        3. Create or update the GitHubAppInstallation record
        4. Sync the accessible repository list
        5. Return context for the redirect response

        Returns a dict with:
          - workspace_id: UUID
          - installation_id: int
          - account_login: str
        """
        state_data = self._state_manager.consume_state(state)
        if not state_data:
            raise GitHubAppError(
                "Invalid or expired state parameter. Please re-initiate "
                "the GitHub App installation."
            )

        workspace_id = uuid.UUID(state_data["workspace_id"])
        user_id = uuid.UUID(state_data["user_id"])

        # Fetch installation info from GitHub
        install_info = self._client.get_installation_info(installation_id)
        account = install_info.get("account", {})

        # Upsert installation record
        installation, created = GitHubAppInstallation.objects.update_or_create(
            installation_id=installation_id,
            defaults={
                "workspace_id": workspace_id,
                "github_account_id": account.get("id", 0),
                "github_account_login": account.get("login", "unknown"),
                "github_account_type": account.get("type", "User"),
                "installed_by_id": user_id,
            },
        )

        # Sync accessible repos (best-effort — installation survives even if sync fails)
        try:
            self._sync_repos(installation)
        except GitHubAppError as exc:
            logger.error(
                "github_app.installation.sync_failed",
                extra={"installation_id": installation_id, "error": str(exc)},
            )

        logger.info(
            "github_app.installation.completed",
            extra={
                "installation_id": installation_id,
                "workspace_id": str(workspace_id),
                "account_login": account.get("login"),
                "created": created,
            },
        )

        return {
            "workspace_id": workspace_id,
            "installation_id": installation_id,
            "account_login": account.get("login", "unknown"),
        }

    # ── Sync Repos from GitHub ────────────────────────────────────────────────

    def _sync_repos(self, installation: GitHubAppInstallation) -> None:
        """
        Fetch the installation's accessible repos from GitHub and replace
        the local cache. Uses a bulk-delete-then-bulk-create strategy
        since the list is authoritative from GitHub.
        """
        github_repos = self._client.list_installation_repos(
            installation.installation_id
        )

        # Delete existing cached repos
        # NOTE: Must use all_objects to bypass SoftDeleteQuerySet (which only
        # sets deleted_at via UPDATE). We need actual row removal here because
        # the unique constraint on (installation_id, github_id) would otherwise
        # conflict with existing soft-deleted rows. A regular QuerySet.delete()
        # issues a real SQL DELETE.
        GitHubAppInstallationRepo.all_objects.filter(installation=installation).delete()

        # Bulk-create new ones
        repo_objs = [
            GitHubAppInstallationRepo(
                installation=installation,
                github_id=repo["id"],
                github_repo=repo["full_name"],
                default_branch=repo.get("default_branch", "main"),
                is_private=repo.get("private", False),
                description=(repo.get("description") or "")[:500] or None,
                language=repo.get("language"),
            )
            for repo in github_repos
        ]
        GitHubAppInstallationRepo.objects.bulk_create(repo_objs, batch_size=100)

        installation.repositories_synced_at = timezone.now()
        installation.save(update_fields=["repositories_synced_at", "updated_at"])

        logger.info(
            "github_app.installation.repos_synced",
            extra={
                "installation_id": installation.installation_id,
                "repo_count": len(repo_objs),
            },
        )

    # ── Refresh Installation Repos ────────────────────────────────────────────

    def refresh_installation(self, installation_id: int) -> GitHubAppInstallation:
        """
        Manually refresh an installation's repo list from GitHub.

        Returns the updated installation instance.
        """
        try:
            installation = GitHubAppInstallation.objects.get(
                installation_id=installation_id, deleted_at__isnull=True
            )
        except GitHubAppInstallation.DoesNotExist as exc:
            raise GitHubAppError(f"Installation {installation_id} not found.") from exc

        self._sync_repos(installation)
        return installation

    # ── Get Repos for Picker ──────────────────────────────────────────────────

    def list_available_repos(
        self, workspace: Workspace, search: str = ""
    ) -> list[GitHubAppInstallationRepo]:
        """
        Return all repos accessible through the workspace's installations.

        The frontend repo picker calls this instead of the old OAuth-based
        list_user_repos. Results are filtered locally by search string.
        """
        installations = GitHubAppInstallation.objects.filter(
            workspace=workspace, deleted_at__isnull=True
        )

        repos = GitHubAppInstallationRepo.objects.filter(installation__in=installations)

        if search.strip():
            repos = repos.filter(github_repo__icontains=search.strip())

        return list(repos.order_by("github_repo"))

    # ── Find Installation for a Repo ──────────────────────────────────────────

    def find_installation_for_repo(
        self, workspace: Workspace, github_repo: str
    ) -> GitHubAppInstallation | None:
        """
        Find which installation in the workspace has access to the given repo.

        Returns None if no installation has this repo.
        """
        repo_record = (
            GitHubAppInstallationRepo.objects.filter(
                installation__workspace=workspace,
                installation__deleted_at__isnull=True,
                github_repo=github_repo,
            )
            .select_related("installation")
            .first()
        )
        return repo_record.installation if repo_record else None

    # ── List Workspace Installations ──────────────────────────────────────────

    def list_installations(self, workspace: Workspace) -> list[GitHubAppInstallation]:
        """
        Return all active installations for a workspace.
        """
        return list(
            GitHubAppInstallation.objects.filter(
                workspace=workspace, deleted_at__isnull=True
            ).order_by("-created_at")
        )

    # ── Remove Installation ───────────────────────────────────────────────────

    @transaction.atomic
    def remove_installation(self, installation_id: int, workspace: Workspace) -> None:
        """
        Soft-delete a GitHub App installation and disconnect its repos.
        """
        try:
            installation = GitHubAppInstallation.objects.get(
                installation_id=installation_id,
                workspace=workspace,
                deleted_at__isnull=True,
            )
        except GitHubAppInstallation.DoesNotExist as exc:
            raise GitHubAppError(
                f"Installation {installation_id} not found in this workspace."
            ) from exc

        # Disconnect repos that were connected through this installation
        from apps.repositories.models import Repository

        Repository.objects.filter(installation=installation).update(installation=None)

        installation.delete()
        _token_cache.invalidate(installation_id)

        logger.info(
            "github_app.installation.removed",
            extra={
                "installation_id": installation_id,
                "workspace_id": str(workspace.id),
            },
        )
