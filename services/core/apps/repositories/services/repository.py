import logging
import uuid
from django.db import transaction
from django.db.models import QuerySet

from apps.workspaces.models import Workspace

from ..events import RepositoryEventPublisher
from ..github_app.client import GitHubAppAPIError as GitHubAppAPIError_
from ..github_app.client import GitHubAppClient, GitHubAppError
from ..github_app.services import GitHubAppInstallationService
from ..models import Repository
from .client import GitHubAPIClient, GitHubTokenClient
from .exceptions import (
    GitHubAPIError,
    RepositoryAlreadyConnectedError,
    RepositoryNotFoundError,
    RepositoryPermissionError,
)

logger = logging.getLogger(__name__)


class RepositoryService:
    def __init__(
        self,
        event_publisher: RepositoryEventPublisher | None = None,
        github_token_client: GitHubTokenClient | None = None,
    ) -> None:
        self._events = event_publisher or RepositoryEventPublisher()
        self._token_client = github_token_client or GitHubTokenClient()

    def connect_repository(
        self, *, workspace: Workspace, actor_id: uuid.UUID, github_repo: str
    ) -> Repository:
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise RepositoryPermissionError(
                "Only workspace admins and owners can connect repositories."
            )
        install_service = GitHubAppInstallationService()
        installation = install_service.find_installation_for_repo(
            workspace=workspace, github_repo=github_repo
        )
        if installation:
            try:
                github_data = GitHubAppClient().get_repository(
                    installation_id=installation.installation_id,
                    github_repo=github_repo,
                )
            except (GitHubAppError, GitHubAppAPIError_) as exc:
                raise GitHubAPIError(str(exc)) from exc
            metadata = GitHubAPIClient.extract_metadata(github_data)
            installation_ref = installation
        else:
            raise GitHubAPIError(
                f"Repository '{github_repo}' is not accessible through any GitHub App "
                "installation in this workspace. Install the GitHub App and grant access "
                "to this repository first."
            )
        with transaction.atomic():
            existing = (
                Repository.all_objects.select_for_update(nowait=False)
                .filter(workspace=workspace, github_id=metadata["github_id"])
                .first()
            )
            if existing and not existing.is_deleted:
                raise RepositoryAlreadyConnectedError(
                    f"Repository '{metadata['github_repo']}' is already connected "
                    "to this workspace."
                )
            if existing and existing.is_deleted:
                for field, value in metadata.items():
                    setattr(existing, field, value)
                existing.deleted_at = None
                existing.connected_by_id = actor_id
                existing.indexed = False
                existing.last_analyzed_at = None
                existing.last_analysis_score = None
                existing.save(
                    update_fields=[
                        *list(metadata.keys()),
                        "deleted_at",
                        "connected_by_id",
                        "indexed",
                        "last_analyzed_at",
                        "last_analysis_score",
                        "updated_at",
                    ]
                )
                repository = existing
            else:
                repository = Repository.objects.create(
                    workspace=workspace,
                    connected_by_id=actor_id,
                    installation=installation_ref,
                    **metadata,
                )
            _repo = repository
            _actor = actor_id
            transaction.on_commit(
                lambda: self._events.repository_connected(
                    repository=_repo, actor_id=_actor
                )
            )
        return repository

    def list_repositories(self, *, workspace: Workspace) -> QuerySet:
        return Repository.objects.filter(workspace=workspace).order_by("-created_at")

    @transaction.atomic
    def disconnect_repository(
        self, *, workspace: Workspace, actor_id: uuid.UUID, repository_id: uuid.UUID
    ) -> None:
        actor_member = workspace.get_member(actor_id)
        if not actor_member or not actor_member.can_admin:
            raise RepositoryPermissionError(
                "Only workspace admins and owners can disconnect repositories."
            )
        try:
            repository = Repository.objects.get(id=repository_id, workspace=workspace)
        except Repository.DoesNotExist as exc:
            raise RepositoryNotFoundError(
                "Repository not found or already disconnected."
            ) from exc
        repository.delete()
        _repo = repository
        _actor = actor_id
        transaction.on_commit(
            lambda: self._events.repository_disconnected(
                repository=_repo, actor_id=_actor
            )
        )
