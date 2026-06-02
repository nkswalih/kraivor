"""
Repository service layer — KRV-021 (Repository Metadata Management).

All business logic lives here — views are thin HTTP adapters.

Service contract:
  - Receives validated data from serializers
  - Enforces business rules (permissions, duplicate detection)
  - Verifies GitHub repository access using the actor's stored OAuth token
  - Fetches repository metadata from the GitHub API
  - Runs DB mutations inside transactions
  - Publishes Kafka events AFTER successful DB commit
  - Raises typed exceptions that views translate to HTTP responses

GitHub token retrieval:
  The actor's GitHub OAuth access token lives in the auth service (OAuthIdentity
  table). The core service has no direct DB access to the auth service, so this
  client makes an internal HTTP call using the X-Internal-Request header to
  bypass JWT verification on the auth service side.

  Auth service endpoint: GET {GITHUB_TOKEN_SERVICE_URL}/api/oauth/github/token/
  Default base URL:      http://auth:8001  (service name in docker-compose)

HTTP client:
  Uses `requests` (already in the project's dependency list) so no extra
  dependency is required. Mirrors the pattern in the auth service's own
  GitHub OAuth client (services/auth/apps/authentication/oauth/github.py).

Transaction design:
  connect_repository() makes two external HTTP calls (auth service + GitHub API)
  before touching the database. To avoid holding a DB connection open during
  network I/O, the permission check and HTTP calls happen outside the transaction,
  and only the DB write uses `with transaction.atomic():`.
"""

import logging
import uuid

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet

from apps.workspaces.models import Workspace

from .events import RepositoryEventPublisher
from .models import Repository

logger = logging.getLogger(__name__)


# ─── Exception hierarchy ──────────────────────────────────────────────────────

class RepositoryServiceError(Exception):
    """Base exception for all repository service errors."""
    pass


class RepositoryPermissionError(RepositoryServiceError):
    """User lacks permission for the requested operation."""
    pass


class RepositoryNotFoundError(RepositoryServiceError):
    """Repository not found or not accessible to the requesting user."""
    pass


class RepositoryAlreadyConnectedError(RepositoryServiceError):
    """Repository is already connected (and active) in this workspace."""
    pass


class GitHubAuthError(RepositoryServiceError):
    """
    User has no linked GitHub account, the stored token is invalid/expired,
    or the auth service was unreachable.
    """
    pass


class GitHubAPIError(RepositoryServiceError):
    """
    GitHub API returned a non-200 response (repo not found, access denied,
    rate limit exceeded, etc.).
    """
    pass


# ─── GitHub Token Client ──────────────────────────────────────────────────────

class GitHubTokenClient:
    """
    Retrieves the actor's GitHub OAuth access token from the auth service.

    The auth service stores OAuth tokens in its OAuthIdentity table. The core
    service has no direct DB access to the auth service, so this client makes
    an internal HTTP call.

    Expected auth service endpoint:
        GET {GITHUB_TOKEN_SERVICE_URL}/api/oauth/github/token/
    Request headers:
        X-Internal-Request: 1       — bypasses JWT verification
        X-User-ID: <user_uuid>      — identifies the requesting user
    Expected success response (HTTP 200):
        {"access_token": "<github_personal_access_token>"}
    Expected not-found response (HTTP 404):
        user has no connected GitHub account
    """

    def get_token(self, user_id: uuid.UUID) -> str:
        """
        Return the GitHub OAuth access token for the given user.

        Raises:
            GitHubAuthError — user has no GitHub account connected,
                              auth service unreachable, or token field missing.
        """
        auth_service_url = getattr(
            settings,
            "GITHUB_TOKEN_SERVICE_URL",
            "http://identity:8001",
        )
        endpoint = f"{auth_service_url}/api/oauth/github/token/"

        try:
            response = requests.get(
                endpoint,
                headers={
                    settings.INTERNAL_REQUEST_HEADER: "1",
                    "X-User-ID": str(user_id),
                },
                timeout=5,
            )
        except requests.exceptions.RequestException as exc:
            logger.error(
                "github.token.fetch.network_error",
                extra={"user_id": str(user_id), "error": str(exc)},
            )
            raise GitHubAuthError(
                "Unable to reach the authentication service. Please try again later."
            ) from exc

        if response.status_code == 404:
            raise GitHubAuthError(
                "No GitHub account connected. "
                "Please connect your GitHub account in workspace settings."
            )

        if response.status_code != 200:
            logger.error(
                "github.token.fetch.unexpected_status",
                extra={"user_id": str(user_id), "status_code": response.status_code},
            )
            raise GitHubAuthError(
                "Failed to retrieve GitHub credentials. "
                "Please reconnect your GitHub account."
            )

        data = response.json()
        token = data.get("access_token") or data.get("token")
        if not token:
            logger.error(
                "github.token.fetch.missing_token",
                extra={"user_id": str(user_id)},
            )
            raise GitHubAuthError(
                "No GitHub access token found. "
                "Please reconnect your GitHub account."
            )

        return token


# ─── GitHub API Client ────────────────────────────────────────────────────────

class GitHubAPIClient:
    """
    Thin wrapper around the GitHub REST API v3.

    Only fetches repository metadata — does not write anything to GitHub.
    Uses the actor's personal OAuth token so we only allow connecting repos
    the user actually has access to; if the user can't read a repo through
    GitHub, they cannot connect it to Kraivor.

    Uses `requests` to match the rest of the project's HTTP client convention.
    """

    GITHUB_API_BASE = "https://api.github.com"

    def __init__(self, access_token: str):
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def get_repository(self, github_repo: str) -> dict:
        """
        Fetch repository metadata from GitHub.

        github_repo: "owner/repo" format, e.g. "acme/api".
        Returns the raw GitHub API response dict.

        Raises:
            GitHubAPIError  — 404, 403, or unexpected non-200
            GitHubAuthError — 401 (token invalid or expired)
        """
        url = f"{self.GITHUB_API_BASE}/repos/{github_repo}"

        try:
            response = requests.get(url, headers=self._headers, timeout=10)
        except requests.exceptions.RequestException as exc:
            logger.error(
                "github.api.network_error",
                extra={"github_repo": github_repo, "error": str(exc)},
            )
            raise GitHubAPIError(
                "Unable to reach GitHub. Please try again later."
            ) from exc

        if response.status_code == 404:
            raise GitHubAPIError(
                f"Repository '{github_repo}' was not found on GitHub or "
                "your account does not have access to it."
            )

        if response.status_code == 403:
            raise GitHubAPIError(
                "GitHub access denied. Your token may be missing the 'repo' scope. "
                "Please reconnect your GitHub account with the required permissions."
            )

        if response.status_code == 401:
            raise GitHubAuthError(
                "Your GitHub token is invalid or has expired. "
                "Please reconnect your GitHub account."
            )

        if response.status_code != 200:
            logger.error(
                "github.api.unexpected_status",
                extra={
                    "github_repo": github_repo,
                    "status_code": response.status_code,
                    "body_preview": response.text[:200],
                },
            )
            raise GitHubAPIError(
                f"GitHub returned an unexpected error (HTTP {response.status_code}). "
                "Please try again later."
            )

        return response.json()

    @staticmethod
    def extract_metadata(github_data: dict) -> dict:
        """
        Map the raw GitHub API response to the fields we store.
        All values are safe-defaulted so a sparse response never causes a KeyError.
        """
        raw_description = github_data.get("description") or ""
        return {
            "github_id": github_data["id"],
            "github_repo": github_data["full_name"],
            "default_branch": github_data.get("default_branch") or "main",
            "language": github_data.get("language") or None,
            "description": raw_description[:500] or None,
            "is_private": bool(github_data.get("private", False)),
        }


# ─── Repository Service ───────────────────────────────────────────────────────

class RepositoryService:
    """
    Handles repository lifecycle: connect, disconnect, list.
    Instantiate per-request. No shared mutable state.
    """

    def __init__(
        self,
        event_publisher: RepositoryEventPublisher | None = None,
        github_token_client: GitHubTokenClient | None = None,
    ):
        self._events = event_publisher or RepositoryEventPublisher()
        self._token_client = github_token_client or GitHubTokenClient()

    # ── Connect ───────────────────────────────────────────────────────────────

    def connect_repository(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        github_repo: str,
    ) -> Repository:
        """
        Connect a GitHub repository to a workspace.

        Steps (in order, transaction as narrow as possible):
          1. Verify actor has admin/owner role — fail fast before any I/O
          2. Fetch actor's GitHub token from the auth service (external HTTP)
          3. Verify repo access and fetch metadata via GitHub API (external HTTP)
          4. Atomic DB write: create new row or restore soft-deleted row
          5. Register post-commit event via transaction.on_commit

        Business rules:
          - Only workspace admins and owners can connect repositories
          - A repository (identified by github_id) can only be connected once
            per workspace; connecting a previously disconnected repo restores it
          - The actor must have a GitHub account linked and access to the repo

        Raises:
            RepositoryPermissionError       — actor is not admin/owner
            RepositoryAlreadyConnectedError — repo is already active in this workspace
            GitHubAuthError                 — no GitHub account or invalid token
            GitHubAPIError                  — GitHub API returned an error
        """
        # ── 1. Permission check (uses prefetched workspace.members) ──────────
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise RepositoryPermissionError(
                "Only workspace admins and owners can connect repositories."
            )

        # ── 2. Fetch GitHub OAuth token (external HTTP — outside transaction) ─
        github_token = self._token_client.get_token(actor_id)

        # ── 3. Call GitHub API (external HTTP — outside transaction) ──────────
        github_data = GitHubAPIClient(github_token).get_repository(github_repo)
        metadata = GitHubAPIClient.extract_metadata(github_data)

        # ── 4. Atomic DB write ────────────────────────────────────────────────
        with transaction.atomic():
            # select_for_update locks the row (if it exists) to prevent two
            # concurrent requests for the same repo from both proceeding past
            # the duplicate check and attempting a double-create.
            existing = (
                Repository.all_objects
                .select_for_update(nowait=False)
                .filter(workspace=workspace, github_id=metadata["github_id"])
                .first()
            )

            if existing and not existing.is_deleted:
                raise RepositoryAlreadyConnectedError(
                    f"Repository '{metadata['github_repo']}' is already connected "
                    "to this workspace."
                )

            if existing and existing.is_deleted:
                # Restore the soft-deleted record and refresh all metadata.
                # Preserves the original PK so historical analysis data retains
                # its repository_id foreign key reference.
                for field, value in metadata.items():
                    setattr(existing, field, value)
                existing.deleted_at = None
                existing.connected_by_id = actor_id
                existing.indexed = False
                existing.last_analyzed_at = None
                existing.last_analysis_score = None
                existing.save(update_fields=[
                    *list(metadata.keys()),
                    "deleted_at",
                    "connected_by_id",
                    "indexed",
                    "last_analyzed_at",
                    "last_analysis_score",
                    "updated_at",
                ])
                repository = existing
            else:
                repository = Repository.objects.create(
                    workspace=workspace,
                    connected_by_id=actor_id,
                    **metadata,
                )

            logger.info(
                "repository.connected",
                extra={
                    "repository_id": str(repository.id),
                    "workspace_id": str(workspace.id),
                    "github_repo": repository.github_repo,
                    "github_id": repository.github_id,
                    "actor_id": str(actor_id),
                },
            )

            # Register event dispatch — fires only after this atomic block commits.
            _repo = repository
            _actor = actor_id
            transaction.on_commit(
                lambda: self._events.repository_connected(
                    repository=_repo,
                    actor_id=_actor,
                )
            )

        return repository

    # ── List ──────────────────────────────────────────────────────────────────

    def list_repositories(self, *, workspace: Workspace) -> QuerySet:
        """
        Return all active (non-deleted) repositories for a workspace.

        Any active workspace member may list repositories — permission is
        enforced at the view layer via workspace membership check.
        Ordered newest-first to match other list endpoints in the service.
        """
        return (
            Repository.objects
            .filter(workspace=workspace)
            .order_by("-created_at")
        )

    # ── Disconnect ────────────────────────────────────────────────────────────

    @transaction.atomic
    def disconnect_repository(
        self,
        *,
        workspace: Workspace,
        actor_id: uuid.UUID,
        repository_id: uuid.UUID,
    ) -> None:
        """
        Disconnect (soft-delete) a repository from a workspace.

        Business rules:
          - Only workspace admins and owners can disconnect repositories
          - Only active (non-deleted) repositories can be disconnected
          - The repository must belong to the specified workspace

        Raises:
            RepositoryPermissionError — actor is not admin/owner
            RepositoryNotFoundError   — repo doesn't exist or is already disconnected
        """
        # ── Permission check ─────────────────────────────────────────────────
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise RepositoryPermissionError(
                "Only workspace admins and owners can disconnect repositories."
            )

        # ── Fetch repository ──────────────────────────────────────────────────
        # Repository.objects uses SoftDeleteManager — only returns active rows.
        try:
            repository = Repository.objects.get(id=repository_id, workspace=workspace)
        except Repository.DoesNotExist as exc:
            raise RepositoryNotFoundError(
                "Repository not found or already disconnected."
            ) from exc

        # ── Soft delete ───────────────────────────────────────────────────────
        # TimestampedModel.delete() sets deleted_at on both the DB row and the
        # in-memory instance — no refresh_from_db() needed after this call.
        repository.delete()

        logger.info(
            "repository.disconnected",
            extra={
                "repository_id": str(repository.id),
                "workspace_id": str(workspace.id),
                "github_repo": repository.github_repo,
                "actor_id": str(actor_id),
            },
        )

        # ── Register event dispatch (post-commit) ─────────────────────────────
        _repo = repository
        _actor = actor_id
        transaction.on_commit(
            lambda: self._events.repository_disconnected(
                repository=_repo,
                actor_id=_actor,
            )
        )